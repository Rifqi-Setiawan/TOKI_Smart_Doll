"""Typed exceptions for session state machine and orchestration (FR-001, FR-002)."""


class SessionFSMError(Exception):
    """Base exception for session state machine errors."""

    pass


class IllegalStateTransitionError(SessionFSMError):
    """Raised when an event is invalid for the current session state."""

    def __init__(self, current_state: str, event: str, reason: str | None = None) -> None:
        self.current_state = current_state
        self.event = event
        self.reason = reason
        msg = f"Illegal transition from '{current_state}' on event '{event}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class StaleCallbackError(SessionFSMError):
    """Raised when callback carries a stale state_version or turn_id (FR-002, ADR-003)."""

    def __init__(
        self,
        session_id: str,
        expected_version: int,
        actual_version: int,
        expected_turn_id: str | None = None,
        actual_turn_id: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        self.expected_turn_id = expected_turn_id
        self.actual_turn_id = actual_turn_id
        super().__init__(
            f"Stale callback for session '{session_id}': expected version {expected_version}, "
            f"got {actual_version} (turn: expected {expected_turn_id}, got {actual_turn_id})"
        )


class SessionTerminalError(SessionFSMError):
    """Raised when an event is dispatched to an already completed or aborted session."""

    def __init__(self, session_id: str, terminal_state: str) -> None:
        self.session_id = session_id
        self.terminal_state = terminal_state
        super().__init__(
            f"Cannot process events for session '{session_id}' in terminal state '{terminal_state}'"
        )


class ConsentRequiredError(SessionFSMError):
    """Raised when starting a session without active guardian consent (FR-003, DATA-010)."""

    pass


class DeviceAuthenticationError(SessionFSMError):
    """Raised when starting a session with an unauthenticated device (FR-003, SEC-002)."""

    pass
