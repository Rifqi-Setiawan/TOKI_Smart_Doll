"""Session states and event vocabulary for the TOKI state machine (FR-001, ADR-003)."""

from enum import Enum


class SessionState(str, Enum):
    """Authoritative finite states of a TOKI interactive session."""

    # Normal lifecycle states
    IDLE = "IDLE"
    SESSION_STARTING = "SESSION_STARTING"
    GREETING = "GREETING"
    ACTIVITY_SELECTING = "ACTIVITY_SELECTING"
    PROMPTING = "PROMPTING"
    LISTENING = "LISTENING"
    INTERPRETING = "INTERPRETING"
    FEEDBACK_PLANNING = "FEEDBACK_PLANNING"
    RESPONDING = "RESPONDING"
    MASTERY_UPDATING = "MASTERY_UPDATING"
    SESSION_ENDING = "SESSION_ENDING"
    COMPLETED = "COMPLETED"

    # Named exceptional states
    NO_SPEECH = "NO_SPEECH"
    LOW_UNDERSTANDING_CONFIDENCE = "LOW_UNDERSTANDING_CONFIDENCE"
    CONTENT_ERROR = "CONTENT_ERROR"
    SAFETY_ESCALATION = "SAFETY_ESCALATION"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    DEPENDENCY_DEGRADED = "DEPENDENCY_DEGRADED"
    SESSION_ABORTED = "SESSION_ABORTED"

    def is_terminal(self) -> bool:
        """Check if this state is a terminal session state."""
        return self in (SessionState.COMPLETED, SessionState.SESSION_ABORTED)

    def is_active(self) -> bool:
        """Check if this state is an active non-terminal interactive state."""
        return not self.is_terminal() and self != SessionState.IDLE


class SessionEvent(str, Enum):
    """Legal runtime events processed by the session state machine."""

    # Normal path lifecycle events
    START_REQUESTED = "session.start"
    LOAD_COMPLETED = "session.load_completed"
    GREETING_DELIVERED = "greeting.delivered"
    ACTIVITY_SELECTED = "activity.selected"
    PROMPT_DELIVERED = "prompt.delivered"
    AUDIO_RECEIVED = "audio.end"
    ATTEMPT_RESOLVED = "attempt.resolved"
    RESPONSE_VALIDATED = "response.validated"
    PLAYBACK_ACKNOWLEDGED = "device.ack"
    MASTERY_COMMITTED = "mastery.committed"
    CLOSING_DELIVERED = "closing.delivered"
    SESSION_FINISHED = "session.finished"

    # Exceptional and branch events
    SILENCE_DETECTED = "audio.silence"
    CONFIDENCE_TOO_LOW = "understanding.low_confidence"
    RETRY_REQUESTED = "turn.retry"
    FALLBACK_TRIGGERED = "turn.fallback"
    TIMEOUT_EXPIRED = "deadline.expired"
    SAFETY_TRIGGERED = "safety.escalation"
    STOP_REQUESTED = "session.stop"
    DEVICE_DISCONNECTED = "device.disconnected"
    DEVICE_RECONNECTED = "device.reconnected"
    INTERNAL_ERROR = "session.internal_error"
