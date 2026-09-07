"""Contract tests for triggered computer vision observations (FR-020, ADR-010, AI-009)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.vision import DetectedObject, VisionObservation, VisionStatus

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_vision_observation_valid_fixture():
    """Valid vision observation fixture parses cleanly."""
    with open(FIXTURES_DIR / "vision_observation_valid.json", encoding="utf-8") as f:
        data = json.load(f)

    obs = VisionObservation.model_validate(data)
    assert obs.status == VisionStatus.DETECTED
    assert len(obs.detected_objects) == 1
    assert obs.detected_objects[0].label == "kucing"
    assert obs.detected_objects[0].confidence == 0.88
    assert obs.freshness_ms == 120
    assert obs.session_id == "sess-987fcdeb-51a2-43f7-9876-543210987654"
    assert obs.state_version == 2


def test_detected_object_bounding_box_validation():
    """Bounding box coordinates must be normalized [0.0 - 1.0]."""
    # Out of bounds coordinate
    with pytest.raises(ValidationError, match="normalized between 0.0 and 1.0"):
        DetectedObject(
            label="buku",
            confidence=0.9,
            bounding_box=[-0.1, 0.0, 1.0, 1.0],
        )

    # Wrong number of coordinates
    with pytest.raises(ValidationError, match="exactly 4 coordinates"):
        DetectedObject(
            label="buku",
            confidence=0.9,
            bounding_box=[0.0, 0.0, 1.0],
        )
