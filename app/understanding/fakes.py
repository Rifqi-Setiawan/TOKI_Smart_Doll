"""Deterministic semantic resolver fakes for testing and offline twin (ADR-006, DEV-004)."""

import asyncio
from typing import Literal

from app.contracts.base import CallbackCorrelation
from app.contracts.understanding import (
    AssessmentReasonCode,
    AssessmentResult,
    AssessmentStatus,
)
from app.providers.exceptions import (
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.understanding.interfaces import SemanticResolver

ResolverMode = Literal["success", "abstain", "uncertain", "timeout", "error"]


class FakeSemanticResolver(SemanticResolver):
    """Deterministic answer evaluator testing exact, substring, and failure modes."""

    def __init__(
        self,
        mode: ResolverMode = "success",
        latency_ms: float = 40.0,
    ) -> None:
        self.mode: ResolverMode = mode
        self.latency_ms = latency_ms
        self.call_count: int = 0

    def set_mode(self, mode: ResolverMode) -> None:
        """Switch simulation mode."""
        self.mode = mode

    async def resolve_intent(
        self,
        transcript: str,
        expected_answers: list[str],
        correlation: CallbackCorrelation | None = None,
        timeout_s: float | None = None,
        target_concept: str = "concept-test",
    ) -> AssessmentResult:
        self.call_count += 1

        session_id = correlation.session_id if correlation else "sess-default-fake"
        turn_id = correlation.turn_id if correlation else "turn-001"
        state_version = correlation.state_version if correlation else 1

        if self.mode == "timeout":
            if timeout_s is not None and timeout_s > 0:
                await asyncio.sleep(timeout_s + 0.05)
            raise ProviderTimeoutError(
                f"Semantic resolution exceeded deadline of {timeout_s}s",
                provider_name="fake_semantic",
            )

        if self.mode == "error":
            raise ProviderUnavailableError(
                "Simulated semantic resolver model crash",
                provider_name="fake_semantic",
            )

        if self.mode == "abstain":
            return AssessmentResult(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=AssessmentStatus.UNCERTAIN,
                target_concept=target_concept,
                matched_phrase=None,
                is_correct=False,
                confidence=0.0,
                reason_code=AssessmentReasonCode.LOW_CONFIDENCE,
                evaluation_latency_ms=self.latency_ms,
            )

        if self.mode == "uncertain":
            # FR-009: UNCERTAIN must NEVER be marked is_correct=True
            return AssessmentResult(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=AssessmentStatus.UNCERTAIN,
                target_concept=target_concept,
                matched_phrase=None,
                is_correct=False,
                confidence=0.45,
                reason_code=AssessmentReasonCode.LOW_CONFIDENCE,
                evaluation_latency_ms=self.latency_ms,
            )

        # Success mode: deterministic string matching against expected answers
        clean_transcript = transcript.strip().lower()
        if not clean_transcript:
            return AssessmentResult(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=AssessmentStatus.NO_RESPONSE,
                target_concept=target_concept,
                matched_phrase=None,
                is_correct=False,
                confidence=1.0,
                reason_code=AssessmentReasonCode.NO_SPEECH_DETECTED,
                evaluation_latency_ms=self.latency_ms,
            )

        for expected in expected_answers:
            clean_expected = expected.strip().lower()
            if clean_transcript == clean_expected:
                return AssessmentResult(
                    session_id=session_id,
                    turn_id=turn_id,
                    state_version=state_version,
                    status=AssessmentStatus.CORRECT,
                    target_concept=target_concept,
                    matched_phrase=clean_expected,
                    is_correct=True,
                    confidence=1.0,
                    reason_code=AssessmentReasonCode.EXACT_MATCH,
                    evaluation_latency_ms=self.latency_ms,
                )
            if clean_expected in clean_transcript:
                return AssessmentResult(
                    session_id=session_id,
                    turn_id=turn_id,
                    state_version=state_version,
                    status=AssessmentStatus.CORRECT,
                    target_concept=target_concept,
                    matched_phrase=clean_expected,
                    is_correct=True,
                    confidence=0.88,
                    reason_code=AssessmentReasonCode.SEMANTIC_RESOLVED,
                    evaluation_latency_ms=self.latency_ms,
                )

        return AssessmentResult(
            session_id=session_id,
            turn_id=turn_id,
            state_version=state_version,
            status=AssessmentStatus.INCORRECT,
            target_concept=target_concept,
            matched_phrase=None,
            is_correct=False,
            confidence=0.92,
            reason_code=AssessmentReasonCode.EXPLICIT_MISMATCH,
            evaluation_latency_ms=self.latency_ms,
        )
