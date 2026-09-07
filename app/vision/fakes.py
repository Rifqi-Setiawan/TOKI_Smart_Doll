"""Deterministic computer vision fakes for testing and offline twin (AI-009, ADR-010, DEV-004)."""

import asyncio
from typing import Literal

from app.contracts.base import CallbackCorrelation
from app.contracts.vision import DetectedObject, VisionObservation, VisionStatus
from app.providers.exceptions import (
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.vision.interfaces import VisionProvider

VisionMode = Literal["success", "unknown", "abstain", "timeout", "error"]


class FakeVisionProvider(VisionProvider):
    """Deterministic object detector returning bounded labels and bounding boxes."""

    def __init__(
        self,
        default_label: str = "kartu_mata",
        default_confidence: float = 0.92,
        mode: VisionMode = "success",
        latency_ms: float = 210.0,
    ) -> None:
        self.default_label = default_label
        self.default_confidence = default_confidence
        self.mode: VisionMode = mode
        self.latency_ms = latency_ms
        self.call_count: int = 0

    def set_mode(self, mode: VisionMode) -> None:
        """Switch simulation mode."""
        self.mode = mode

    async def detect_objects(
        self,
        frame_bytes: bytes,
        allowed_vocabulary: list[str] | None = None,
        correlation: CallbackCorrelation | None = None,
        timeout_s: float | None = None,
    ) -> VisionObservation:
        self.call_count += 1

        session_id = correlation.session_id if correlation else "sess-default-fake"
        turn_id = correlation.turn_id if correlation else "turn-001"
        state_version = correlation.state_version if correlation else 1

        if self.mode == "timeout":
            if timeout_s is not None and timeout_s > 0:
                await asyncio.sleep(timeout_s + 0.05)
            raise ProviderTimeoutError(
                f"Vision detection exceeded deadline of {timeout_s}s",
                provider_name="fake_vision",
            )

        if self.mode == "error":
            raise ProviderUnavailableError(
                "Simulated vision model processing error",
                provider_name="fake_vision",
            )

        if self.mode == "abstain":
            return VisionObservation(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=VisionStatus.ABSTAIN,
                detected_objects=[],
                freshness_ms=50,
                latency_ms=self.latency_ms,
                provider="fake_vision",
                model_version="fake-yolo-v1",
            )

        if self.mode == "unknown":
            return VisionObservation(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=VisionStatus.UNKNOWN,
                detected_objects=[
                    DetectedObject(
                        label="unknown_object",
                        confidence=0.42,
                        bounding_box=[0.1, 0.1, 0.8, 0.8],
                    )
                ],
                freshness_ms=50,
                latency_ms=self.latency_ms,
                provider="fake_vision",
                model_version="fake-yolo-v1",
            )

        # Check vocabulary filtering (AI-009)
        label = self.default_label
        if allowed_vocabulary is not None and label not in allowed_vocabulary:
            return VisionObservation(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=VisionStatus.UNKNOWN,
                detected_objects=[],
                freshness_ms=50,
                latency_ms=self.latency_ms,
                provider="fake_vision",
                model_version="fake-yolo-v1",
            )

        return VisionObservation(
            session_id=session_id,
            turn_id=turn_id,
            state_version=state_version,
            status=VisionStatus.DETECTED,
            detected_objects=[
                DetectedObject(
                    label=label,
                    confidence=self.default_confidence,
                    bounding_box=[0.2, 0.2, 0.6, 0.6],
                )
            ],
            freshness_ms=50,
            latency_ms=self.latency_ms,
            provider="fake_vision",
            model_version="fake-yolo-v1",
        )
