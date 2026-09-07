"""TOKI versioned domain and API contracts package (API-001)."""

from app.contracts.base import CURRENT_SCHEMA_VERSION, CallbackCorrelation, ContractModel
from app.contracts.device import (
    AudioMetadata,
    AudioSpec,
    CodecType,
    CommandType,
    DeviceAck,
    DeviceCommand,
    DeviceEnvelope,
    DeviceEvent,
    DisplayState,
    EnvelopeType,
    EventType,
    GestureType,
)
from app.contracts.errors import ErrorCode, ErrorResponse
from app.contracts.mastery import (
    AssistanceLevel,
    LearningEvidence,
    MasteryBand,
    MasteryUpdate,
)
from app.contracts.progress import (
    ChildProgressDTO,
    SessionSummaryDTO,
    SkillProgressDTO,
)
from app.contracts.response import (
    ContentProvenance,
    PedagogicalAct,
    ResponsePlan,
)
from app.contracts.speech import (
    ASRResult,
    ASRStatus,
    TTSResult,
    TTSSource,
)
from app.contracts.understanding import (
    AssessmentReasonCode,
    AssessmentResult,
    AssessmentStatus,
)
from app.contracts.vision import (
    DetectedObject,
    VisionObservation,
    VisionStatus,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "ContractModel",
    "CallbackCorrelation",
    "EnvelopeType",
    "CommandType",
    "EventType",
    "CodecType",
    "DisplayState",
    "GestureType",
    "AudioSpec",
    "AudioMetadata",
    "DeviceAck",
    "DeviceCommand",
    "DeviceEvent",
    "DeviceEnvelope",
    "ASRStatus",
    "TTSSource",
    "ASRResult",
    "TTSResult",
    "AssessmentStatus",
    "AssessmentReasonCode",
    "AssessmentResult",
    "PedagogicalAct",
    "ContentProvenance",
    "ResponsePlan",
    "VisionStatus",
    "DetectedObject",
    "VisionObservation",
    "MasteryBand",
    "AssistanceLevel",
    "LearningEvidence",
    "MasteryUpdate",
    "SkillProgressDTO",
    "SessionSummaryDTO",
    "ChildProgressDTO",
    "ErrorCode",
    "ErrorResponse",
]
