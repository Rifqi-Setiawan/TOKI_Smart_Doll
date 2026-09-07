"""Response planning and pedagogical intent contracts (FR-011, FR-012, ADR-007, AI-008)."""

from enum import Enum

from pydantic import Field, field_validator

from app.contracts.base import ContractModel
from app.contracts.device import DisplayState, GestureType


class PedagogicalAct(str, Enum):
    """Categorization of communicative intent in learning interaction (FR-011)."""

    PROMPT = "PROMPT"
    PRAISE = "PRAISE"
    CORRECTIVE_FEEDBACK = "CORRECTIVE_FEEDBACK"
    HINT = "HINT"
    RETRY_PROMPT = "RETRY_PROMPT"
    ESCALATION = "ESCALATION"
    CLOSING = "CLOSING"


class ContentProvenance(ContractModel):
    """Traceability metadata linking output to approved curriculum (FR-011, ADR-007)."""

    curriculum_version: str = Field(description="Approved curriculum version")
    module_id: str = Field(description="Curriculum module ID (e.g. 'family', 'animals')")
    activity_id: str = Field(description="Activity definition ID")
    template_id: str = Field(description="Approved template phrase ID")


class ResponsePlan(ContractModel):
    """Deterministic plan for the child-facing spoken, visual, and physical feedback (FR-011)."""

    plan_id: str = Field(description="Unique response plan identifier")
    session_id: str = Field(description="Session correlation identifier")
    turn_id: str = Field(description="Turn correlation identifier")
    pedagogical_act: PedagogicalAct = Field(description="Type of learning feedback")
    approved_text: str = Field(description="Approved baseline template text")
    spoken_text: str = Field(
        description="Actual text to speak (approved template or verified paraphrase)"
    )
    audio_asset_id: str = Field(description="Pre-generated audio asset fallback ID (ADR-009)")
    provenance: ContentProvenance = Field(description="Curriculum audit provenance")
    display: DisplayState = Field(default=DisplayState.SPEAKING, description="Facial expression")
    gesture: GestureType = Field(default=GestureType.NOD, description="Physical movement")
    is_escalation: bool = Field(default=False, description="True if safety escalation triggered")
    paraphrase_applied: bool = Field(
        default=False, description="True if bounded paraphraser modified text"
    )

    @field_validator("spoken_text")
    @classmethod
    def validate_spoken_word_limit(cls, value: str) -> str:
        # AI-008: Maximum 25 spoken words to avoid cognitive overload for ages 3-6
        words = value.strip().split()
        if len(words) > 25:
            raise ValueError(
                f"AI-008 violation: Spoken response has {len(words)} words, exceeding max 25 words"
            )
        return value
