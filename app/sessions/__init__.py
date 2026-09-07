"""Session state machine and orchestration package (FR-001, FR-002, ADR-003)."""

from app.sessions.activity_slice import ActivityExecutionResult, DeterministicActivitySlice
from app.sessions.exceptions import (
    ConsentRequiredError,
    IllegalStateTransitionError,
    SessionFSMError,
    SessionTerminalError,
    StaleCallbackError,
)
from app.sessions.orchestrator import SessionOrchestrator
from app.sessions.policies import ActivityPolicy, SessionContext
from app.sessions.state_machine import TransitionResult, compute_transition
from app.sessions.states import SessionEvent, SessionState

__all__ = [
    "ActivityExecutionResult",
    "ActivityPolicy",
    "ConsentRequiredError",
    "DeterministicActivitySlice",
    "IllegalStateTransitionError",
    "SessionContext",
    "SessionEvent",
    "SessionFSMError",
    "SessionOrchestrator",
    "SessionState",
    "SessionTerminalError",
    "StaleCallbackError",
    "TransitionResult",
    "compute_transition",
]
