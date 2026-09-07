"""Curriculum domain module for approved activity validation, immutability, and access."""

from app.curriculum.approval import CurriculumApprovalManager
from app.curriculum.exceptions import (
    CurriculumError,
    CurriculumImmutabilityError,
    CurriculumNotFoundError,
    CurriculumRevokedError,
    CurriculumUnapprovedError,
    CurriculumValidationError,
)
from app.curriculum.importer import CurriculumImporter
from app.curriculum.models import (
    ActivityAudioReferences,
    ActivityDifficulty,
    ActivityProvenance,
    AnswerSpec,
    CurriculumActivity,
    CurriculumManifest,
    ReviewStatus,
    SkillDefinition,
)
from app.curriculum.service import CurriculumService

__all__ = [
    "ActivityAudioReferences",
    "ActivityDifficulty",
    "ActivityProvenance",
    "AnswerSpec",
    "CurriculumActivity",
    "CurriculumApprovalManager",
    "CurriculumError",
    "CurriculumImmutabilityError",
    "CurriculumImporter",
    "CurriculumManifest",
    "CurriculumNotFoundError",
    "CurriculumRevokedError",
    "CurriculumService",
    "CurriculumUnapprovedError",
    "CurriculumValidationError",
    "ReviewStatus",
    "SkillDefinition",
]
