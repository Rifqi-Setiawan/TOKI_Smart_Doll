"""Vendor-neutral interfaces for bounded computer vision observation (AI-001, AI-009, ADR-010)."""

from abc import ABC, abstractmethod

from app.contracts.base import CallbackCorrelation
from app.contracts.vision import VisionObservation


class VisionProvider(ABC):
    """Abstract interface for triggered, bounded object detection (ADR-010, AI-009)."""

    @abstractmethod
    async def detect_objects(
        self,
        frame_bytes: bytes,
        allowed_vocabulary: list[str] | None = None,
        correlation: CallbackCorrelation | None = None,
        timeout_s: float | None = None,
    ) -> VisionObservation:
        """Detect physical learning objects from snapshot frames.

        Filter detections against allowed curriculum vocabulary; unknown objects map
        to UNKNOWN status.
        """
        pass
