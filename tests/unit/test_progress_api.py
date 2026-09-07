"""Unit tests for parent-facing progress API endpoints (FR-016, SEC-010)."""

from fastapi.testclient import TestClient

from app.contracts.progress import CLINICAL_TERMS_PATTERN, ChildProgressDTO


def test_get_child_progress_success(test_client: TestClient) -> None:
    """GET /api/v1/progress/{child_id} returns valid non-clinical ChildProgressDTO."""
    response = test_client.get("/api/v1/progress/child-demo-001")
    assert response.status_code == 200
    data = response.json()

    # Verify DTO validity through Pydantic
    dto = ChildProgressDTO.model_validate(data)
    assert dto.child_id == "child-demo-001"
    assert dto.display_name == "Sahabat Toki"
    assert dto.age_band == "3-4 tahun"

    # Verify SEC-010: zero clinical copy
    for session in dto.recent_sessions:
        assert not CLINICAL_TERMS_PATTERN.search(session.parent_tip)


def test_get_child_progress_invalid_child_id(test_client: TestClient) -> None:
    """GET /api/v1/progress/ with empty/whitespace ID is rejected."""
    response = test_client.get("/api/v1/progress/%20")
    assert response.status_code in (400, 404)
