"""Unit tests for curriculum importer and immutability (FR-007, DATA-003)."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.exceptions import (
    CurriculumImmutabilityError,
    CurriculumValidationError,
)
from app.curriculum.importer import CurriculumImporter
from app.persistence.database import get_engine, get_session_maker
from app.persistence.models import (
    Base,
    CurriculumItem,
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = get_session_maker(engine)
    async with session_maker() as session:
        yield session

    await engine.dispose()


def load_pilot_pack() -> dict[str, Any]:
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "curriculum"
        / "pilot_body_parts_pack.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_importer_reports_field_level_errors(db_session: AsyncSession) -> None:
    """Acceptance Criterion 5: Import validation reports detailed field-level errors."""
    importer = CurriculumImporter(db_session)

    # Empty payload
    is_valid, errors = importer.validate_manifest({})
    assert is_valid is False
    assert any("version_token" in e for e in errors)
    assert any("description" in e for e in errors)
    assert any("activities" in e for e in errors)

    # Activity missing fallback_audio_id (ADR-009 requirement)
    invalid_manifest = {
        "version_token": "test-v1.0",
        "description": "Test Pack",
        "activities": [
            {
                "activity_token": "act_1",
                "module": "test",
                "skill_token": "skill_1",
                "prompt_text": "Coba sebutkan...",
                "answer_spec": {"exact_matches": ["jawaban"]},
                "audio_refs": {},  # missing fallback_audio_id
            }
        ],
    }
    is_valid, errors = importer.validate_manifest(invalid_manifest)
    assert is_valid is False
    assert any("fallback_audio_id" in e for e in errors)

    with pytest.raises(CurriculumValidationError) as exc_info:
        await importer.import_manifest(invalid_manifest)
    assert len(exc_info.value.errors) > 0


@pytest.mark.asyncio
async def test_importer_successful_and_idempotent_draft_import(
    db_session: AsyncSession,
) -> None:
    """Acceptance Criterion 5: Import succeeds and re-importing DRAFT is idempotent."""
    importer = CurriculumImporter(db_session)
    data = load_pilot_pack()
    data["version_token"] = "curr-draft-v1.0"
    data["status"] = "DRAFT"

    # 1. Initial import
    ver = await importer.import_manifest(data)
    assert ver.version_token == "curr-draft-v1.0"
    assert ver.status == "DRAFT"

    # Verify database counts
    items_stmt = select(CurriculumItem).where(CurriculumItem.curriculum_version_id == ver.id)
    items_res = await db_session.execute(items_stmt)
    assert len(list(items_res.scalars().all())) == 4

    # 2. Re-importing DRAFT updates idempotently without duplicating rows
    ver2 = await importer.import_manifest(data)
    assert ver2.id == ver.id

    items_res2 = await db_session.execute(items_stmt)
    assert len(list(items_res2.scalars().all())) == 4


@pytest.mark.asyncio
async def test_importer_rejects_overwriting_approved_version(
    db_session: AsyncSession,
) -> None:
    """Acceptance Criterion 3 & 5: Approved versions are immutable; re-import is rejected."""
    importer = CurriculumImporter(db_session)
    data = load_pilot_pack()
    data["version_token"] = "curr-approved-v1.0"
    data["status"] = "APPROVED"

    # 1. Import approved version
    await importer.import_manifest(data)

    # 2. Attempt to re-import or mutate the approved version
    with pytest.raises(CurriculumImmutabilityError) as exc_info:
        await importer.import_manifest(data)

    assert "APPROVED and immutable" in str(exc_info.value)
