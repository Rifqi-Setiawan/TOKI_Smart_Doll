"""Parent-facing progress API router (FR-016, SEC-010, DATA-008)."""

from fastapi import APIRouter, HTTPException

from app.analytics.projector import EventProjector
from app.contracts.progress import ChildProgressDTO

router = APIRouter(prefix="/api/v1/progress", tags=["Progress"])

# Default in-memory projector instance for local / test profiles
_default_projector = EventProjector()


def get_projector() -> EventProjector:
    """Dependency provider for the event projector."""
    return _default_projector


@router.get("/{child_id}", response_model=ChildProgressDTO)
async def get_child_progress(
    child_id: str,
) -> ChildProgressDTO:
    """Retrieve encouraging, non-clinical learning progress summary for parents (FR-016).

    Invariants (SEC-010, DATA-008):
    - Pseudonymous child identifier only.
    - Zero clinical, diagnostic, or pathological terminology.
    - Encouraging home-engagement parent tips only.
    """
    if not child_id or not child_id.strip():
        raise HTTPException(status_code=400, detail="Invalid child_id parameter")

    projector = get_projector()
    return projector.get_child_progress(child_id)
