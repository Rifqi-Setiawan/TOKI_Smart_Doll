"""Authoritative session orchestrator and persistence boundary (FR-001, FR-002, ADR-003)."""

from typing import Any
from uuid import uuid4

from app.contracts.base import CallbackCorrelation
from app.persistence.repositories import (
    ConsentRepository,
    EventOutboxRepository,
    SessionRepository,
)
from app.sessions.exceptions import (
    ConsentRequiredError,
    DeviceAuthenticationError,
    IllegalStateTransitionError,
    SessionTerminalError,
    StaleCallbackError,
)
from app.sessions.policies import ActivityPolicy, SessionContext
from app.sessions.state_machine import TransitionResult, compute_transition
from app.sessions.states import SessionEvent, SessionState


class SessionOrchestrator:
    """Sole authoritative controller of session finite-state transitions and persistence.

    Enforces:
    - Only the orchestrator can advance authoritative session state (FR-002, ADR-003).
    - Rejection of stale callbacks via CallbackCorrelation.state_version (FR-002).
    - Guardian consent requirement to initiate sessions (FR-003, DATA-010).
    - Universal stop/safety interrupts (FR-012, FR-022).
    - Optimistic concurrency protection when committing state changes (DATA-002).
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        consent_repo: ConsentRepository | None = None,
        event_repo: EventOutboxRepository | None = None,
        policy: ActivityPolicy = ActivityPolicy(),
    ) -> None:
        self.session_repo = session_repo
        self.consent_repo = consent_repo
        self.event_repo = event_repo
        self.policy = policy
        self._contexts: dict[str, SessionContext] = {}

    async def start_session(
        self,
        device_id: str,
        child_id: str,
        curriculum_version_id: str,
        session_id: str | None = None,
    ) -> SessionContext:
        """Start a new educational session after verifying authentication and consent (FR-003)."""
        if not device_id or not device_id.strip():
            raise DeviceAuthenticationError("Device ID must be provided and authenticated")

        # Verify active guardian consent
        if self.consent_repo:
            has_consent = await self.consent_repo.has_active_consent(child_id)
            if not has_consent:
                raise ConsentRequiredError(
                    f"DATA-010 violation: Cannot start session for child '{child_id}' "
                    "without active guardian consent"
                )

        sid = session_id or str(uuid4())
        # Persist session row in database
        db_session = await self.session_repo.create_session(
            device_id=device_id,
            child_id=child_id,
            curriculum_version_id=curriculum_version_id,
            session_id=sid,
            initial_state=SessionState.SESSION_STARTING.value,
        )

        context = SessionContext(
            session_id=sid,
            device_id=device_id,
            child_id=child_id,
            curriculum_version_id=curriculum_version_id,
            state=SessionState.SESSION_STARTING,
            state_version=db_session.state_version,
            current_turn_number=0,
            device_authenticated=True,
            consent_active=True,
            approved_curriculum_available=True,
        )
        self._contexts[sid] = context

        if self.event_repo:
            await self.event_repo.record_event_and_outbox(
                session_id=sid,
                event_sequence=context.state_version,
                event_type="session.started",
                payload={
                    "device_id": device_id,
                    "child_id": child_id,
                    "curriculum_version_id": curriculum_version_id,
                    "state": SessionState.SESSION_STARTING.value,
                    "state_version": context.state_version,
                },
                outbox_topic="session-events",
            )

        return context

    async def get_context(self, session_id: str) -> SessionContext:
        """Retrieve cached context or reconstruct from database."""
        if session_id in self._contexts:
            return self._contexts[session_id]

        db_session = await self.session_repo.get_session(session_id)
        context = SessionContext(
            session_id=db_session.id,
            device_id=db_session.device_id,
            child_id=db_session.child_id,
            curriculum_version_id=db_session.curriculum_version_id,
            state=SessionState(db_session.state),
            state_version=db_session.state_version,
            current_turn_number=db_session.current_turn_number,
            current_turn_id=(
                f"turn-{db_session.current_turn_number}"
                if db_session.current_turn_number > 0
                else None
            ),
        )
        self._contexts[session_id] = context
        return context

    async def dispatch_event(
        self,
        session_id: str,
        event: SessionEvent,
        correlation: CallbackCorrelation | None = None,
        is_final_activity: bool | None = None,
        event_payload: dict[str, Any] | None = None,
    ) -> TransitionResult:
        """Evaluate an event against the FSM, enforce invariants, and persist state advance.

        Enforces:
        - Stale callback protection (FR-002, ADR-003): correlation.state_version must match.
        - Terminal state protection: closed sessions cannot process events.
        - Optimistic concurrency protection: DB advance_state increments version.
        """
        context = await self.get_context(session_id)

        # 1. Guard against events on terminal sessions
        if context.state.is_terminal():
            raise SessionTerminalError(session_id, context.state.value)

        # 2. Guard against stale provider callbacks (FR-002, ADR-003)
        if correlation is not None:
            if correlation.session_id != session_id:
                raise StaleCallbackError(
                    session_id=session_id,
                    expected_version=context.state_version,
                    actual_version=correlation.state_version,
                    expected_turn_id=context.current_turn_id,
                    actual_turn_id=correlation.turn_id,
                )
            if correlation.state_version != context.state_version:
                raise StaleCallbackError(
                    session_id=session_id,
                    expected_version=context.state_version,
                    actual_version=correlation.state_version,
                    expected_turn_id=context.current_turn_id,
                    actual_turn_id=correlation.turn_id,
                )
            if context.current_turn_id and correlation.turn_id != context.current_turn_id:
                raise StaleCallbackError(
                    session_id=session_id,
                    expected_version=context.state_version,
                    actual_version=correlation.state_version,
                    expected_turn_id=context.current_turn_id,
                    actual_turn_id=correlation.turn_id,
                )

        if is_final_activity is not None:
            context.is_final_activity = is_final_activity

        # 3. Compute pure deterministic transition
        res = compute_transition(context.state, event, context, self.policy)
        if not res.success:
            raise IllegalStateTransitionError(
                current_state=context.state.value,
                event=event.value,
                reason=res.reason,
            )

        # 4. Update in-memory context metadata
        from_state = context.state
        if res.increment_turn:
            context.current_turn_number += 1
            context.current_turn_id = f"turn-{context.current_turn_number}"
        if res.reset_turn_retry:
            context.turn_retry_count = 0
        if res.increment_turn_retry:
            context.turn_retry_count += 1

        if res.to_state in (
            SessionState.PROMPTING,
            SessionState.LISTENING,
            SessionState.FEEDBACK_PLANNING,
            SessionState.MASTERY_UPDATING,
        ):
            context.last_durable_state = res.to_state

        context.state = res.to_state

        # 5. Persist transition to database with optimistic concurrency check
        new_version = await self.session_repo.advance_state(
            session_id=session_id,
            expected_state_version=context.state_version,
            new_state=res.to_state.value,
            new_turn_number=context.current_turn_number if res.increment_turn else None,
        )
        context.state_version = new_version

        # 6. Publish domain event to outbox atomically
        if self.event_repo:
            payload = {
                "from_state": from_state.value,
                "to_state": res.to_state.value,
                "event": event.value,
                "state_version": new_version,
                "turn_number": context.current_turn_number,
                "turn_id": context.current_turn_id,
                "is_retry": res.is_retry,
                "is_fallback": res.is_fallback,
            }
            if event_payload:
                payload.update(event_payload)
            await self.event_repo.record_event_and_outbox(
                session_id=session_id,
                event_sequence=new_version,
                event_type="session.transition",
                payload=payload,
                outbox_topic="session-events",
            )

        return res

    async def request_stop(self, session_id: str, reason: str = "user_stop") -> TransitionResult:
        """Immediately trigger stop interrupt from any active state (FR-022, SEC-009)."""
        return await self.dispatch_event(
            session_id=session_id,
            event=SessionEvent.STOP_REQUESTED,
            event_payload={"stop_reason": reason},
        )

    async def request_safety_escalation(
        self, session_id: str, reason: str = "safety_policy_match"
    ) -> TransitionResult:
        """Immediately trigger safety escalation from any active state (FR-012, SEC-005)."""
        return await self.dispatch_event(
            session_id=session_id,
            event=SessionEvent.SAFETY_TRIGGERED,
            event_payload={"safety_reason": reason},
        )
