"""Unit tests for curriculum approval lifecycle, immutability, and version forking (DATA-003)."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.approval import CurriculumApprovalManager
from app.curriculum.exceptions import CurriculumImmutabilityError
from app.curriculum.importer import CurriculumImporter
from app.persistence.database import get_engine, get_session_maker
from app.persistence.models import (
    Base,
    CurriculumItem,
)
from app.persistence.repositories import (
    CurriculumRepository,
    ImmutabilityViolationError,
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


@pytest.mark.asyncio
async def test_approval_flow_and_immutability_enforcement(
    db_session: AsyncSession,
) -> None:
    """Acceptance Criterion 3: Changes create a new immutable version with reviewer provenance."""
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "curriculum"
        / "pilot_body_parts_pack.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Start with DRAFT release
    data["version_token"] = "curr-review-v1.0"
    data["status"] = "DRAFT"

    importer = CurriculumImporter(db_session)
    await importer.import_manifest(data)

    approval = CurriculumApprovalManager(db_session)
    repo = CurriculumRepository(db_session)

    # Draft items CAN be modified prior to approval
    await repo.update_item_prompt(
        curriculum_version_id=(await approval.get_version("curr-review-v1.0")).id,
        item_token="body_parts_mata",
        new_prompt="Draft modified prompt: apa yang untuk melihat?",
    )

    # 2. Formally APPROVE the version with pedagogical expert ID
    reviewer_id = "dr_susanti_sp_a_paud_expert@toki.id"
    approved_ver = await approval.approve_version("curr-review-v1.0", reviewer_id)
    assert approved_ver.status == "APPROVED"
    assert approved_ver.approved_by == reviewer_id
    assert approved_ver.approved_at is not None

    # 3. Any direct modification to approved version is rejected (DATA-003)
    with pytest.raises(ImmutabilityViolationError) as exc_info:
        await repo.update_item_prompt(
            curriculum_version_id=approved_ver.id,
            item_token="body_parts_mata",
            new_prompt="Illegal prompt mutation on approved content!",
        )
    assert "Approved curriculum version" in str(exc_info.value)
    assert "is immutable" in str(exc_info.value)

    # 4. Fork a new version for pedagogical changes (DATA-003)
    forked_ver = await approval.fork_new_version(
        source_version_token="curr-review-v1.0",
        new_version_token="curr-review-v2.0",
        created_by="curriculum_editor@toki.id",
    )
    assert forked_ver.status == "DRAFT"
    assert forked_ver.approved_by is None
    assert forked_ver.version_token == "curr-review-v2.0"

    # Forked draft CAN be modified
    await repo.update_item_prompt(
        curriculum_version_id=forked_ver.id,
        item_token="body_parts_mata",
        new_prompt="V2 prompt: Coba tunjukkan matamu!",
    )

    # Verify original approved version remains completely untouched
    stmt_v1 = select(CurriculumItem).where(
        CurriculumItem.curriculum_version_id == approved_ver.id,
        CurriculumItem.item_token == "body_parts_mata",
    )
    v1_item = (await db_session.execute(stmt_v1)).scalar_one()
    assert v1_item.prompt_text == "Draft modified prompt: apa yang untuk melihat?"


@pytest.mark.asyncio
async def test_revocation_lifecycle(db_session: AsyncSession) -> None:
    """Revoking an approved version marks it REVOKED and blocks re-approval."""
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "curriculum"
        / "pilot_body_parts_pack.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    data["version_token"] = "curr-revoke-v1.0"
    data["status"] = "APPROVED"
    data["reviewed_by"] = "reviewer@toki.id"

    importer = CurriculumImporter(db_session)
    await importer.import_manifest(data)

    approval = CurriculumApprovalManager(db_session)

    # Revoke version
    revoked = await approval.revoke_version(
        version_token="curr-revoke-v1.0",
        reason="Found typo in prompt",
        reviewer_id="lead_reviewer@toki.id",
    )
    assert revoked.status == "REVOKED"

    # Re-approval is rejected
    with pytest.raises(CurriculumImmutabilityError):
        await approval.approve_version("curr-revoke-v1.0", "lead_reviewer@toki.id")
