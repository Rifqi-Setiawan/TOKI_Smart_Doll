"""Computer vision adapter module containing neutral interfaces and deterministic fakes."""

from app.vision.fakes import FakeVisionProvider
from app.vision.interfaces import VisionProvider

__all__ = [
    "FakeVisionProvider",
    "VisionProvider",
]
