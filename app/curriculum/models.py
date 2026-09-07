"""Curriculum domain contracts and activity specification schema (FR-006, FR-007, DATA-003)."""

from enum import Enum

from pydantic import Field, field_validator

from app.contracts.base import ContractModel


class ReviewStatus(str, Enum):
    """Pedagogical content review status (FR-006, DATA-003)."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REVOKED = "REVOKED"
    ARCHIVED = "ARCHIVED"


class ActivityDifficulty(int, Enum):
    """Pedagogical scaffolding difficulty level for early childhood education."""

    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3


class AnswerSpec(ContractModel):
    """Deterministic expected answer rules and pronunciation variations (FR-007, FR-008)."""

    exact_matches: list[str] = Field(
        min_length=1,
        description="Canonical correct answers in Indonesian (e.g. ['mata'])",
    )
    synonyms: list[str] = Field(
        default_factory=list,
        description="Accepted synonyms and colloquial terms (e.g. ['kedua mata', 'netra'])",
    )
    phonetic_variations: list[str] = Field(
        default_factory=list,
        description="Tolerated toddler phonological variations (e.g. ['matak', 'matah'])",
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether match is case-sensitive (default False)",
    )

    @field_validator("exact_matches")
    @classmethod
    def validate_non_empty_strings(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values if v.strip()]
        if not cleaned:
            raise ValueError("exact_matches must contain at least one non-empty string")
        return cleaned

    def all_accepted_tokens(self) -> list[str]:
        """Return combined unique list of all accepted token strings in lower case."""
        tokens = set()
        for s in self.exact_matches + self.synonyms + self.phonetic_variations:
            norm = s if self.case_sensitive else s.lower()
            tokens.add(norm)
        return sorted(tokens)


class ActivityAudioReferences(ContractModel):
    """Audio asset identifiers for cache-first and pre-recorded offline rendering (ADR-009)."""

    prompt_audio_id: str | None = Field(
        default=None,
        description="Asset ID for the main question prompt audio",
    )
    fallback_audio_id: str = Field(
        description="Mandatory offline pre-recorded fallback audio asset ID (ADR-009)",
    )
    hint_audio_ids: list[str] = Field(
        default_factory=list,
        description="Asset IDs for spoken scaffolding hints",
    )


class CurriculumActivity(ContractModel):
    """Structured child-facing turn activity schema (FR-007)."""

    activity_token: str = Field(
        description="Unique item token within curriculum version (e.g. 'body_parts_mata')"
    )
    module: str = Field(description="Domain module (e.g. 'body_parts', 'animals', 'colors')")
    skill_token: str = Field(description="Target skill token (e.g. 'body_parts')")
    difficulty: ActivityDifficulty = Field(
        default=ActivityDifficulty.BEGINNER,
        description="Graduated difficulty (1=Beginner, 2=Intermediate, 3=Advanced)",
    )
    prompt_text: str = Field(
        min_length=5,
        description="Child-friendly Indonesian prompt spoken by TOKI",
    )
    answer_spec: AnswerSpec = Field(
        description="Typed answer matching specification",
    )
    hints: list[str] = Field(
        default_factory=list,
        description="Scaffolding hints delivered upon hesitation or first retry (FR-010)",
    )
    retry_prompt: str | None = Field(
        default=None,
        description="Alternative gentler prompt for the single child-friendly retry",
    )
    audio_refs: ActivityAudioReferences = Field(
        description="Pre-recorded audio asset references",
    )
    review_notes: str | None = Field(
        default=None,
        description="Pedagogical reviewer notes or curriculum alignment",
    )

    @field_validator("prompt_text")
    @classmethod
    def validate_prompt_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("prompt_text cannot be blank")
        return trimmed


class SkillDefinition(ContractModel):
    """Pedagogical skill descriptor within a curriculum release."""

    skill_token: str = Field(description="Unique skill identifier (e.g. 'body_parts')")
    name: str = Field(description="Human-readable title (e.g. 'Mengenal Anggota Tubuh')")
    domain: str = Field(default="language", description="Domain classification")
    target_age_band: str = Field(default="4-6", description="Target age band")


class CurriculumManifest(ContractModel):
    """Complete curriculum package manifest for import, review, and approval (FR-006, DATA-003)."""

    version_token: str = Field(description="Unique release token (e.g. 'curriculum-v1.0')")
    status: ReviewStatus = Field(
        default=ReviewStatus.DRAFT,
        description="Review lifecycle status",
    )
    description: str = Field(
        description="Curriculum release description and pedagogical goals",
    )
    target_age_band: str = Field(
        default="4-6",
        description="Target developmental age band",
    )
    reviewed_by: str | None = Field(
        default=None,
        description="Pedagogical expert reviewer identifier (DATA-003)",
    )
    reviewed_at: str | None = Field(
        default=None,
        description="ISO timestamp of qualified review approval",
    )
    skills: list[SkillDefinition] = Field(
        default_factory=list,
        description="Skills defined in this release",
    )
    activities: list[CurriculumActivity] = Field(
        default_factory=list,
        description="Turn activities defined in this release",
    )


class ActivityProvenance(ContractModel):
    """Audit and runtime provenance DTO for retrieved activities (ADR-005, DATA-007)."""

    curriculum_version_token: str = Field(description="Release version token")
    curriculum_version_id: str = Field(description="Database UUID of curriculum version")
    curriculum_status: ReviewStatus = Field(description="Approved status at query time")
    approved_by: str | None = Field(default=None, description="Pedagogical reviewer ID")
    approved_at: str | None = Field(default=None, description="Approval timestamp")
    item_id: str = Field(description="Database UUID of curriculum item")
    item_token: str = Field(description="Activity item token")
    skill_id: str = Field(description="Database UUID of parent skill")
    skill_token: str = Field(description="Skill token")
    skill_name: str = Field(description="Human-readable skill name")
    module: str = Field(description="Module category")
    difficulty: int = Field(description="Difficulty level (1-3)")
    prompt_text: str = Field(description="Active prompt text")
    answer_spec: AnswerSpec = Field(description="Answer specification")
    hints: list[str] = Field(default_factory=list, description="Scaffolding hints")
    retry_prompt: str | None = Field(default=None, description="Single retry prompt")
    audio_refs: ActivityAudioReferences = Field(description="Audio references")
