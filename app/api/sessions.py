"""Session and turn execution API endpoints (FR-001, FR-003, FR-014, REL-005)."""

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.understanding import AssessmentStatus
from app.persistence.database import get_db_session, get_session_maker
from app.persistence.repositories import NotFoundError, SessionRepository
from app.sessions.activity_slice import DeterministicActivitySlice
from app.sessions.states import SessionEvent

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider for database session."""
    session_maker = get_session_maker()
    async with get_db_session(session_maker) as session:
        yield session


class StartSessionRequest(BaseModel):
    """Request to initiate a new educational session."""

    device_id: str = Field(default="dev-demo-001", description="Physical/simulated device ID")
    child_id: str = Field(default="child-demo-001", description="Pseudonymous child ID")
    curriculum_version_id: str = Field(
        default="curr-v1.0", description="Approved curriculum version"
    )
    session_id: str | None = Field(default=None, description="Optional explicit session ID")


class SessionResponseDTO(BaseModel):
    """DTO representing current session state and version."""

    session_id: str
    device_id: str
    child_id: str
    state: str
    state_version: int
    current_turn_number: int


class SubmitTurnRequest(BaseModel):
    """Request to submit a simulated child answer turn."""

    activity_token: str = Field(
        default="body_parts_mata", description="Target approved curriculum item token"
    )
    version_token: str = Field(
        default="curriculum-v1.0", description="Approved curriculum version token"
    )
    answer_text: str | None = Field(default=None, description="Simulated child answer text")
    simulate_silence: bool = Field(default=False, description="Simulate silence / no speech")
    simulate_low_confidence: bool = Field(
        default=False, description="Simulate low confidence / uncertain"
    )
    is_final_activity: bool = Field(default=True, description="Whether this ends the session")


class TurnExecutionResponseDTO(BaseModel):
    """DTO representing turn execution outcome."""

    session_id: str
    turn_id: str
    turn_number: int
    activity_token: str
    prompt_text: str
    answer_text: str | None
    assessment_status: str
    is_correct: bool
    is_uncertain: bool
    confidence: float
    pedagogical_act: str
    spoken_text: str
    session_state: str
    state_version: int
    is_duplicate: bool
    is_safe: bool
    orchestration_latency_ms: float
    persistence_latency_ms: float
    total_latency_ms: float


class StopSessionRequest(BaseModel):
    """Request to immediately stop an active session."""

    reason: str = Field(default="user_stop", description="Reason for stopping")


@router.post("", response_model=SessionResponseDTO, status_code=status.HTTP_201_CREATED)
async def start_session(
    body: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionResponseDTO:
    """Start a new educational session verifying device auth and guardian consent (FR-003)."""
    slice_runner = DeterministicActivitySlice(db)
    try:
        ctx = await slice_runner.start_session(
            device_id=body.device_id,
            child_id=body.child_id,
            curriculum_version_id=body.curriculum_version_id,
            session_id=body.session_id,
        )
        await db.commit()
        return SessionResponseDTO(
            session_id=ctx.session_id,
            device_id=ctx.device_id,
            child_id=ctx.child_id,
            state=ctx.state.value,
            state_version=ctx.state_version,
            current_turn_number=ctx.current_turn_number,
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=SessionResponseDTO)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResponseDTO:
    """Retrieve current session state by ID."""
    repo = SessionRepository(db)
    try:
        sess = await repo.get_session(session_id)
        return SessionResponseDTO(
            session_id=sess.id,
            device_id=sess.device_id,
            child_id=sess.child_id,
            state=sess.state,
            state_version=sess.state_version,
            current_turn_number=sess.current_turn_number,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found") from exc


@router.post("/{session_id}/turns", response_model=TurnExecutionResponseDTO)
async def submit_turn(
    session_id: str,
    body: SubmitTurnRequest,
    db: AsyncSession = Depends(get_db),
) -> TurnExecutionResponseDTO:
    """Execute one complete deterministic activity turn (FR-001, FR-008, FR-011, FR-014)."""
    slice_runner = DeterministicActivitySlice(db)
    try:
        # 1. Prompt activity
        activity, _ = await slice_runner.prompt_activity(
            session_id=session_id,
            version_token=body.version_token,
            item_token=body.activity_token,
        )

        # 2. Execute turn
        res = await slice_runner.execute_turn(
            session_id=session_id,
            activity=activity,
            answer_text=body.answer_text,
            simulate_silence=body.simulate_silence,
            simulate_low_confidence=body.simulate_low_confidence,
            is_final_activity=body.is_final_activity,
        )
        await db.commit()

        return TurnExecutionResponseDTO(
            session_id=res.session_id,
            turn_id=res.turn_id,
            turn_number=res.turn_number,
            activity_token=res.activity_token,
            prompt_text=res.prompt_text,
            answer_text=res.answer_text,
            assessment_status=res.assessment.status.value,
            is_correct=res.assessment.is_correct,
            is_uncertain=res.assessment.status
            in (
                AssessmentStatus.UNCERTAIN,
                AssessmentStatus.AMBIGUOUS,
                AssessmentStatus.NO_RESPONSE,
            ),
            confidence=res.assessment.confidence,
            pedagogical_act=res.response_plan.pedagogical_act.value,
            spoken_text=res.response_plan.spoken_text,
            session_state=res.session_state.value,
            state_version=res.state_version,
            is_duplicate=res.is_duplicate,
            is_safe=res.is_safe,
            orchestration_latency_ms=res.orchestration_latency_ms,
            persistence_latency_ms=res.persistence_latency_ms,
            total_latency_ms=res.total_latency_ms,
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/stop", response_model=SessionResponseDTO)
async def stop_session(
    session_id: str,
    body: StopSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionResponseDTO:
    """Immediately stop an active session safely (FR-022, SEC-009)."""
    slice_runner = DeterministicActivitySlice(db)
    try:
        await slice_runner.orchestrator.request_stop(session_id=session_id, reason=body.reason)
        await slice_runner.orchestrator.dispatch_event(
            session_id=session_id,
            event=SessionEvent.CLOSING_DELIVERED,
        )
        await db.commit()
        ctx = await slice_runner.orchestrator.get_context(session_id)
        return SessionResponseDTO(
            session_id=ctx.session_id,
            device_id=ctx.device_id,
            child_id=ctx.child_id,
            state=ctx.state.value,
            state_version=ctx.state_version,
            current_turn_number=ctx.current_turn_number,
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
