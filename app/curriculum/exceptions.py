"""Typed domain exceptions for curriculum access and immutability (FR-006, DATA-003)."""


class CurriculumError(Exception):
    """Base exception for all curriculum domain and service errors."""

    pass


class CurriculumNotFoundError(CurriculumError):
    """Raised when a requested curriculum version, skill, or activity item does not exist."""

    pass


class CurriculumUnapprovedError(CurriculumError):
    """Raised when attempting to access a DRAFT curriculum version in a live session (FR-006)."""

    pass


class CurriculumRevokedError(CurriculumError):
    """Raised when attempting to access a REVOKED or ARCHIVED curriculum version (FR-006)."""

    pass


class CurriculumImmutabilityError(CurriculumError):
    """Raised when attempting to mutate or overwrite an APPROVED version (DATA-003)."""

    pass


class CurriculumValidationError(CurriculumError):
    """Raised when activity specification or package manifest fails validation (FR-007)."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []
