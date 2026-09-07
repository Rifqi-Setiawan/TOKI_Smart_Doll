"""Turn tracer and isolated telemetry export engine (OBS-001, OBS-002, OBS-004, FR-021)."""

import logging
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime

from app.telemetry.models import TurnTrace
from app.telemetry.redaction import redact_sensitive_payload

logger = logging.getLogger("toki.telemetry")


class TurnTracer:
    """Records and exports per-turn traces with complete failure isolation (OBS-004)."""

    def __init__(
        self,
        max_buffer_size: int = 1000,
        exporter: Callable[[TurnTrace], None] | None = None,
    ) -> None:
        self.traces: deque[TurnTrace] = deque(maxlen=max_buffer_size)
        self.exporter = exporter
        self.exporter_failures_count: int = 0

    def record_trace(self, trace: TurnTrace) -> None:
        """Store trace in memory and safely attempt export without blocking turn execution.

        Invariant (OBS-004): Exporter crashes or network outages MUST NEVER propagate.
        """
        # 1. Local in-memory retention for operator view (FR-021)
        self.traces.append(trace)

        # 2. Asynchronous / isolated export attempt
        if self.exporter is not None:
            try:
                self.exporter(trace)
            except Exception as exc:
                self.exporter_failures_count += 1
                logger.warning(
                    "OBS-004 Telemetry export failure swallowed: %s (trace_id=%s)",
                    exc,
                    trace.trace_id,
                )

    def get_trace(self, trace_id: str) -> TurnTrace | None:
        """Retrieve a trace by trace ID."""
        for t in reversed(self.traces):
            if t.trace_id == trace_id:
                return t
        return None

    def get_traces_for_session(self, session_id: str) -> list[TurnTrace]:
        """Retrieve all traces associated with a session."""
        return [t for t in self.traces if t.session_id == session_id]

    @classmethod
    def create_trace(
        cls,
        session_id: str,
        turn_id: str,
        turn_number: int,
        message_id: str,
        state_before: str,
        state_after: str,
        state_version: int,
        curriculum_version: str,
        module_id: str,
        activity_id: str,
        template_id: str,
        item_token: str,
        assessment_status: str,
        is_correct: bool,
        confidence: float,
        reason_code: str,
        pedagogical_act: str,
        spoken_text: str,
        audio_asset_id: str,
        assessment_latency_ms: float,
        total_turn_latency_ms: float,
        is_escalation: bool = False,
        paraphrase_applied: bool = False,
        fallback_used: bool = False,
        previous_mastery_band: str | None = None,
        new_mastery_band: str | None = None,
        mastery_explanation_code: str | None = None,
        mastery_transition_reason: str | None = None,
        created_at: datetime | None = None,
    ) -> TurnTrace:
        """Helper to build a sanitized, validated TurnTrace."""
        # Scrub spoken text if needed
        clean_text = str(redact_sensitive_payload(spoken_text))
        is_uncertain = assessment_status in ("UNCERTAIN", "NO_RESPONSE", "AMBIGUOUS")

        return TurnTrace(
            session_id=session_id,
            turn_id=turn_id,
            turn_number=turn_number,
            message_id=message_id,
            state_before=state_before,
            state_after=state_after,
            state_version=state_version,
            curriculum_version=curriculum_version,
            module_id=module_id,
            activity_id=activity_id,
            template_id=template_id,
            item_token=item_token,
            assessment_status=assessment_status,
            is_correct=is_correct,
            confidence=confidence,
            reason_code=reason_code,
            is_uncertain=is_uncertain,
            pedagogical_act=pedagogical_act,
            spoken_text=clean_text,
            audio_asset_id=audio_asset_id,
            is_escalation=is_escalation,
            paraphrase_applied=paraphrase_applied,
            fallback_used=fallback_used,
            previous_mastery_band=previous_mastery_band,
            new_mastery_band=new_mastery_band,
            mastery_explanation_code=mastery_explanation_code,
            mastery_transition_reason=mastery_transition_reason,
            assessment_latency_ms=assessment_latency_ms,
            total_turn_latency_ms=total_turn_latency_ms,
            created_at=created_at or datetime.now(UTC),
        )


# Global default turn tracer singleton
default_tracer = TurnTracer()
