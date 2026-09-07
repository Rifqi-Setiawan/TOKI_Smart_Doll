"""Deterministic End-to-End Activity Slice Coordinator.

Implements the unified orchestration boundary for one complete deterministic activity
without external AI, linking device protocol, session state machine, curriculum retrieval,
deterministic answer assessment, response planning, atomic persistence, event projection,
and turn observability.

Requirements: REL-005, DEV-002, EVAL-001, FR-001-017, OBS-001-005, SEC-004, SEC-005, SEC-009.
Architecture/ADR: ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.projector import EventProjector
from app.contracts.base import CallbackCorrelation
from app.contracts.device import (
    CommandType,
    DeviceCommand,
    DeviceEnvelope,
    EnvelopeType,
    EventType,
)
from app.contracts.response import ResponsePlan
from app.contracts.understanding import (
    AssessmentReasonCode,
    AssessmentResult,
    AssessmentStatus,
)
from app.curriculum.models import ActivityProvenance
from app.curriculum.service import CurriculumService
from app.device_protocol.recovery import ProtocolRecoveryManager
from app.device_protocol.sequencing import ProtocolSequencer
from app.persistence.models import utc_now
from app.persistence.repositories import (
    ConsentRepository,
    EventOutboxRepository,
    ProtocolRepository,
    SessionRepository,
)
from app.persistence.unit_of_work import ResolvedTurnOutcome, ResolvedTurnUnitOfWork
from app.response.planner import ResponsePlanner
from app.safety.policy import SafetyEvaluation, SafetyPolicyEvaluator
from app.sessions.orchestrator import SessionOrchestrator
from app.sessions.policies import ActivityPolicy, SessionContext
from app.sessions.states import SessionEvent, SessionState
from app.telemetry.models import TurnTrace
from app.telemetry.tracer import TurnTracer
from app.understanding.deterministic_assessor import DeterministicAssessor
from simulators.device_simulator import DeviceSimulator


@dataclass(frozen=True)
class ActivityExecutionResult:
    """Result of executing an activity turn through the deterministic slice."""

    session_id: str
    turn_id: str
    turn_number: int
    activity_token: str
    prompt_text: str
    answer_text: str | None
    assessment: AssessmentResult
    response_plan: ResponsePlan
    session_state: SessionState
    state_version: int
    is_duplicate: bool
    is_retry: bool
    is_fallback: bool
    is_safe: bool
    uow_outcome: ResolvedTurnOutcome | None
    trace: TurnTrace | None
    orchestration_latency_ms: float
    persistence_latency_ms: float
    total_latency_ms: float


class DeterministicActivitySlice:
    """Coordinates the deterministic activity vertical slice end-to-end."""

    def __init__(
        self,
        db_session: AsyncSession,
        device_simulator: DeviceSimulator | None = None,
        policy: ActivityPolicy = ActivityPolicy(),
    ) -> None:
        self.db_session = db_session
        self.policy = policy
        self.simulator = device_simulator or DeviceSimulator(device_serial="TOKI-DEMO-001")

        # Repositories
        self.session_repo = SessionRepository(db_session)
        self.consent_repo = ConsentRepository(db_session)
        self.event_repo = EventOutboxRepository(db_session)
        self.protocol_repo = ProtocolRepository(db_session)

        # Core Engines
        self.orchestrator = SessionOrchestrator(
            session_repo=self.session_repo,
            consent_repo=self.consent_repo,
            event_repo=self.event_repo,
            policy=policy,
        )
        self.sequencer = ProtocolSequencer(
            protocol_repo=self.protocol_repo,
            session_repo=self.session_repo,
        )
        self.recovery = ProtocolRecoveryManager(
            protocol_repo=self.protocol_repo,
            session_repo=self.session_repo,
        )
        self.curriculum = CurriculumService(db_session)
        self.assessor = DeterministicAssessor()
        self.safety = SafetyPolicyEvaluator()
        self.planner = ResponsePlanner(safety_evaluator=self.safety)
        self.uow = ResolvedTurnUnitOfWork(db_session)
        self.projector = EventProjector()
        self.tracer = TurnTracer()

    async def start_session(
        self,
        device_id: str = "dev-demo-001",
        child_id: str = "child-demo-001",
        curriculum_version_id: str = "curr-v1.0",
        session_id: str | None = None,
    ) -> SessionContext:
        """Start a new session and advance to ACTIVITY_SELECTING via FSM."""
        # 1. Start session in orchestrator (checks auth and guardian consent)
        ctx = await self.orchestrator.start_session(
            device_id=device_id,
            child_id=child_id,
            curriculum_version_id=curriculum_version_id,
            session_id=session_id,
        )

        # 2. Handshake from device simulator
        handshake_env = self.simulator.create_handshake_envelope(ctx.session_id)
        val = await self.sequencer.validate_and_record_inbound(handshake_env)
        if not val.valid:
            raise ValueError(f"Handshake failed: {val.message}")

        # 3. Transition: SESSION_STARTING -> GREETING -> ACTIVITY_SELECTING
        await self.orchestrator.dispatch_event(
            session_id=ctx.session_id,
            event=SessionEvent.LOAD_COMPLETED,
        )
        await self.orchestrator.dispatch_event(
            session_id=ctx.session_id,
            event=SessionEvent.GREETING_DELIVERED,
        )

        await self.db_session.flush()
        return await self.orchestrator.get_context(ctx.session_id)

    async def prompt_activity(
        self,
        session_id: str,
        version_token: str = "curriculum-v1.0",
        item_token: str = "body_parts_mata",
    ) -> tuple[ActivityProvenance, DeviceEnvelope]:
        """Select an approved activity and deliver prompt envelope to simulator."""
        activity = await self.curriculum.get_active_activity(version_token, item_token)

        # Transition: ACTIVITY_SELECTING -> PROMPTING
        await self.orchestrator.dispatch_event(
            session_id=session_id,
            event=SessionEvent.ACTIVITY_SELECTED,
        )
        ctx = await self.orchestrator.get_context(session_id)

        # Build outbound prompt command envelope
        prompt_cmd = DeviceCommand(
            command_type=CommandType.SPEAK,
            parameters={
                "text": activity.prompt_text,
                "audio_asset_id": activity.audio_refs.prompt_audio_id,
                "fallback_asset_id": activity.audio_refs.fallback_audio_id,
            },
        )
        cursor = await self.protocol_repo.get_or_create_cursor(session_id)
        seq_num = cursor.last_outbound_seq + 1
        prompt_env = DeviceEnvelope(
            message_id=str(uuid4()),
            session_id=session_id,
            turn_id=ctx.current_turn_id,
            seq=seq_num,
            timestamp_ms=int(time.time() * 1000),
            type=EnvelopeType.COMMAND,
            command=prompt_cmd,
        )
        await self.recovery.record_sent_command(session_id, prompt_env)

        # Simulator receives command and ACKs
        self.simulator.receive_command(prompt_cmd.model_dump())
        ack_env = self.simulator.create_ack_envelope(
            session_id=session_id,
            acked_message_id=prompt_env.message_id,
            original_seq=seq_num,
        )
        ack_res = await self.recovery.process_ack(session_id, ack_env)
        if not ack_res.valid:
            raise ValueError(f"ACK processing failed: {ack_res.message}")

        # Transition: PROMPTING -> LISTENING
        await self.orchestrator.dispatch_event(
            session_id=session_id,
            event=SessionEvent.PROMPT_DELIVERED,
        )

        await self.db_session.flush()
        return activity, prompt_env

    async def execute_turn(
        self,
        session_id: str,
        activity: ActivityProvenance,
        answer_text: str | None = None,
        simulate_silence: bool = False,
        simulate_low_confidence: bool = False,
        custom_envelope: DeviceEnvelope | None = None,
        is_final_activity: bool = True,
    ) -> ActivityExecutionResult:
        """Execute one complete answer assessment turn through the deterministic slice."""
        start_total = time.perf_counter()
        ctx = await self.orchestrator.get_context(session_id)
        turn_id = ctx.current_turn_id or "turn-1"
        turn_num = ctx.current_turn_number

        correlation = CallbackCorrelation(
            session_id=session_id,
            turn_id=turn_id,
            state_version=ctx.state_version,
        )

        # 1. Check for Duplicate Envelope / Monotonic Sequencing (FR-004, SEC-004)
        inbound_env = custom_envelope
        if inbound_env is None:
            seq = self.simulator._next_sequence()
            inbound_env = DeviceEnvelope(
                message_id=str(uuid4()),
                session_id=session_id,
                turn_id=turn_id,
                seq=seq,
                timestamp_ms=int(time.time() * 1000),
                type=EnvelopeType.EVENT,
                event={
                    "event_type": EventType.BUTTON_PRESSED.value,
                    "metadata": {"answer": answer_text},
                },
            )

        val_result = await self.sequencer.validate_and_record_inbound(
            inbound_env,
            expected_state_version=ctx.state_version,
            expected_turn_id=turn_id,
        )

        if val_result.is_duplicate:
            # Replay / Duplicate detected: zero duplicate side-effects (FR-004, DATA-004)
            return ActivityExecutionResult(
                session_id=session_id,
                turn_id=turn_id,
                turn_number=turn_num,
                activity_token=activity.item_token,
                prompt_text=activity.prompt_text,
                answer_text=answer_text,
                assessment=AssessmentResult(
                    session_id=session_id,
                    turn_id=turn_id,
                    state_version=ctx.state_version,
                    status=AssessmentStatus.NO_RESPONSE,
                    target_concept=activity.skill_name,
                    confidence=0.0,
                    reason_code=AssessmentReasonCode.NO_SPEECH_DETECTED,
                ),
                response_plan=self.planner.plan_generic_fallback(session_id, turn_id),
                session_state=ctx.state,
                state_version=ctx.state_version,
                is_duplicate=True,
                is_retry=False,
                is_fallback=False,
                is_safe=True,
                uow_outcome=None,
                trace=None,
                orchestration_latency_ms=0.0,
                persistence_latency_ms=0.0,
                total_latency_ms=(time.perf_counter() - start_total) * 1000.0,
            )

        # 2. Check for Safety Violation / Explicit Stop
        is_safe = True
        safety_eval: SafetyEvaluation | None = None
        if answer_text:
            safety_eval = self.safety.evaluate_text(answer_text)
            if not safety_eval.is_safe:
                is_safe = False

        if not is_safe and safety_eval:
            # Safety Escalation (FR-012, SEC-005)
            await self.orchestrator.request_safety_escalation(
                session_id=session_id,
                reason=safety_eval.reason or "safety_policy_violation",
            )
            response_plan = self.planner.plan_safety_override(
                session_id=session_id,
                turn_id=turn_id,
                safety_eval=safety_eval,
                curriculum_version=activity.curriculum_version_token,
            )
            await self.orchestrator.dispatch_event(
                session_id=session_id,
                event=SessionEvent.CLOSING_DELIVERED,
            )
            await self.db_session.flush()
            now_ctx = await self.orchestrator.get_context(session_id)
            return ActivityExecutionResult(
                session_id=session_id,
                turn_id=turn_id,
                turn_number=turn_num,
                activity_token=activity.item_token,
                prompt_text=activity.prompt_text,
                answer_text=answer_text,
                assessment=AssessmentResult(
                    session_id=session_id,
                    turn_id=turn_id,
                    state_version=ctx.state_version,
                    status=AssessmentStatus.UNCERTAIN,
                    target_concept=activity.skill_name,
                    confidence=0.0,
                    reason_code=AssessmentReasonCode.LOW_CONFIDENCE,
                ),
                response_plan=response_plan,
                session_state=now_ctx.state,
                state_version=now_ctx.state_version,
                is_duplicate=False,
                is_retry=False,
                is_fallback=False,
                is_safe=False,
                uow_outcome=None,
                trace=None,
                orchestration_latency_ms=0.0,
                persistence_latency_ms=0.0,
                total_latency_ms=(time.perf_counter() - start_total) * 1000.0,
            )

        # Explicit Stop Request Check (FR-022, SEC-009)
        if answer_text and answer_text.strip().lower() == "stop":
            await self.orchestrator.request_stop(session_id=session_id, reason="user_stop")
            response_plan = self.planner.plan_safe_stop(
                session_id=session_id,
                turn_id=turn_id,
                curriculum_version=activity.curriculum_version_token,
            )
            await self.orchestrator.dispatch_event(
                session_id=session_id,
                event=SessionEvent.CLOSING_DELIVERED,
            )
            await self.db_session.flush()
            now_ctx = await self.orchestrator.get_context(session_id)
            return ActivityExecutionResult(
                session_id=session_id,
                turn_id=turn_id,
                turn_number=turn_num,
                activity_token=activity.item_token,
                prompt_text=activity.prompt_text,
                answer_text=answer_text,
                assessment=AssessmentResult(
                    session_id=session_id,
                    turn_id=turn_id,
                    state_version=ctx.state_version,
                    status=AssessmentStatus.NO_RESPONSE,
                    target_concept=activity.skill_name,
                    confidence=1.0,
                    reason_code=AssessmentReasonCode.NO_SPEECH_DETECTED,
                ),
                response_plan=response_plan,
                session_state=now_ctx.state,
                state_version=now_ctx.state_version,
                is_duplicate=False,
                is_retry=False,
                is_fallback=False,
                is_safe=True,
                uow_outcome=None,
                trace=None,
                orchestration_latency_ms=0.0,
                persistence_latency_ms=0.0,
                total_latency_ms=(time.perf_counter() - start_total) * 1000.0,
            )

        # 3. Process Inbound Answer & FSM advance: LISTENING -> INTERPRETING or NO_SPEECH
        start_orch = time.perf_counter()
        is_retry = False
        is_fallback = False

        if simulate_silence or not answer_text or not answer_text.strip():
            # Silence / No Speech (FR-009, FR-010)
            await self.orchestrator.dispatch_event(
                session_id=session_id,
                event=SessionEvent.SILENCE_DETECTED,
                correlation=correlation,
            )
            assessment = AssessmentResult(
                session_id=session_id,
                turn_id=turn_id,
                state_version=correlation.state_version,
                status=AssessmentStatus.NO_RESPONSE,
                target_concept=activity.skill_name,
                is_correct=False,
                confidence=1.0,
                reason_code=AssessmentReasonCode.NO_SPEECH_DETECTED,
            )
            # Evaluate bounded retry (FR-010)
            if ctx.turn_retry_count < self.policy.max_turn_retries:
                await self.orchestrator.dispatch_event(
                    session_id=session_id,
                    event=SessionEvent.RETRY_REQUESTED,
                )
                is_retry = True
            else:
                await self.orchestrator.dispatch_event(
                    session_id=session_id,
                    event=SessionEvent.FALLBACK_TRIGGERED,
                )
                is_fallback = True

        else:
            # Child Answer Received: advance to INTERPRETING
            await self.orchestrator.dispatch_event(
                session_id=session_id,
                event=SessionEvent.AUDIO_RECEIVED,
                correlation=correlation,
            )
            correlation = CallbackCorrelation(
                session_id=session_id,
                turn_id=turn_id,
                state_version=(await self.orchestrator.get_context(session_id)).state_version,
            )

            # Deterministic Answer Assessment (FR-008, FR-009)
            if simulate_low_confidence:
                assessment = AssessmentResult(
                    session_id=session_id,
                    turn_id=turn_id,
                    state_version=correlation.state_version,
                    status=AssessmentStatus.UNCERTAIN,
                    target_concept=activity.skill_name,
                    is_correct=False,
                    confidence=0.42,
                    reason_code=AssessmentReasonCode.LOW_CONFIDENCE,
                )
            else:
                assessment = self.assessor.assess(
                    evidence=answer_text,
                    answer_spec=activity.answer_spec,
                    target_concept=activity.skill_name,
                    correlation=correlation,
                )

            # Invariant FR-009: Low confidence or uncertain is NEVER marked incorrect
            if assessment.status in (
                AssessmentStatus.UNCERTAIN,
                AssessmentStatus.AMBIGUOUS,
                AssessmentStatus.NO_RESPONSE,
            ):
                await self.orchestrator.dispatch_event(
                    session_id=session_id,
                    event=SessionEvent.CONFIDENCE_TOO_LOW,
                    correlation=correlation,
                )
                if ctx.turn_retry_count < self.policy.max_turn_retries:
                    await self.orchestrator.dispatch_event(
                        session_id=session_id,
                        event=SessionEvent.RETRY_REQUESTED,
                    )
                    is_retry = True
                else:
                    await self.orchestrator.dispatch_event(
                        session_id=session_id,
                        event=SessionEvent.FALLBACK_TRIGGERED,
                    )
                    is_fallback = True
            else:
                # Answer resolved (correct or incorrect)
                await self.orchestrator.dispatch_event(
                    session_id=session_id,
                    event=SessionEvent.ATTEMPT_RESOLVED,
                    correlation=correlation,
                )

        # 4. Response Planning (FR-011)
        response_plan = self.planner.plan_response(
            session_id=session_id,
            turn_id=turn_id,
            assessment=assessment,
            activity=activity,
            turn_retry_count=ctx.turn_retry_count,
            raw_transcript=answer_text,
        )

        curr_ctx = await self.orchestrator.get_context(session_id)
        if curr_ctx.state == SessionState.FEEDBACK_PLANNING:
            await self.orchestrator.dispatch_event(
                session_id=session_id,
                event=SessionEvent.RESPONSE_VALIDATED,
            )
            # Device acknowledges playback
            await self.orchestrator.dispatch_event(
                session_id=session_id,
                event=SessionEvent.PLAYBACK_ACKNOWLEDGED,
            )

        orch_latency = (time.perf_counter() - start_orch) * 1000.0

        # 5. Atomic Persistence Unit of Work (FR-014, FR-015, DATA-004, DATA-005)
        start_persist = time.perf_counter()
        uow_outcome: ResolvedTurnOutcome | None = None
        now_ctx = await self.orchestrator.get_context(session_id)

        if now_ctx.state == SessionState.MASTERY_UPDATING:
            target_next_state = (
                SessionState.SESSION_ENDING if is_final_activity else SessionState.ACTIVITY_SELECTING
            )
            uow_outcome = await self.uow.execute(
                session_id=session_id,
                turn_number=turn_num,
                message_id=inbound_env.message_id,
                item_token=activity.item_token,
                skill_token=activity.skill_token,
                expected_state_version=now_ctx.state_version,
                new_session_state=target_next_state.value,
                assessment=assessment,
                response_plan=response_plan,
            )

            # Sync in-memory orchestrator state
            now_ctx.state = target_next_state
            now_ctx.state_version = uow_outcome.state_version
            self.orchestrator._contexts[session_id] = now_ctx

            # Transition out of ending to COMPLETED if final
            if is_final_activity:
                await self.orchestrator.dispatch_event(
                    session_id=session_id,
                    event=SessionEvent.CLOSING_DELIVERED,
                )

        persist_latency = (time.perf_counter() - start_persist) * 1000.0

        # 6. Event Projection & Observability (FR-016, FR-017, OBS-001, OBS-002)
        await self.projector.consume_pending_outbox(self.db_session)
        await self.db_session.flush()

        final_ctx = await self.orchestrator.get_context(session_id)
        total_latency = (time.perf_counter() - start_total) * 1000.0

        # Build complete root trace
        trace = TurnTrace(
            trace_id=f"trace-{uuid4().hex[:12]}",
            session_id=session_id,
            turn_id=turn_id,
            turn_number=turn_num,
            message_id=inbound_env.message_id,
            created_at=utc_now(),
            state_before=ctx.state.value,
            state_after=final_ctx.state.value,
            state_version=final_ctx.state_version,
            curriculum_version=activity.curriculum_version_token,
            module_id=activity.module,
            activity_id=activity.item_token,
            template_id=response_plan.provenance.template_id,
            item_token=activity.item_token,
            assessment_status=assessment.status.value,
            is_correct=assessment.is_correct,
            confidence=assessment.confidence,
            reason_code=assessment.reason_code.value,
            is_uncertain=(
                assessment.status
                in (
                    AssessmentStatus.UNCERTAIN,
                    AssessmentStatus.AMBIGUOUS,
                    AssessmentStatus.NO_RESPONSE,
                )
            ),
            pedagogical_act=response_plan.pedagogical_act.value,
            spoken_text=response_plan.spoken_text,
            audio_asset_id=response_plan.audio_asset_id,
            is_escalation=response_plan.is_escalation,
            fallback_used=is_fallback,
            previous_mastery_band=(
                uow_outcome.mastery_result.previous_band.value
                if uow_outcome and uow_outcome.mastery_result
                else None
            ),
            new_mastery_band=(
                uow_outcome.mastery_result.new_band.value
                if uow_outcome and uow_outcome.mastery_result
                else None
            ),
            mastery_explanation_code=(
                uow_outcome.mastery_result.explanation_code
                if uow_outcome and uow_outcome.mastery_result
                else None
            ),
            assessment_latency_ms=assessment.evaluation_latency_ms,
            total_turn_latency_ms=round(total_latency, 2),
        )
        self.tracer.record_trace(trace)

        return ActivityExecutionResult(
            session_id=session_id,
            turn_id=turn_id,
            turn_number=turn_num,
            activity_token=activity.item_token,
            prompt_text=activity.prompt_text,
            answer_text=answer_text,
            assessment=assessment,
            response_plan=response_plan,
            session_state=final_ctx.state,
            state_version=final_ctx.state_version,
            is_duplicate=False,
            is_retry=is_retry,
            is_fallback=is_fallback,
            is_safe=is_safe,
            uow_outcome=uow_outcome,
            trace=trace,
            orchestration_latency_ms=round(orch_latency, 2),
            persistence_latency_ms=round(persist_latency, 2),
            total_latency_ms=round(total_latency, 2),
        )
