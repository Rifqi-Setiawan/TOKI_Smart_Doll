"""Unit tests for runtime curriculum query service and provenance tracking (FR-006, ADR-005)."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.approval import CurriculumApprovalManager
from app.curriculum.exceptions import (
    CurriculumRevokedError,
    CurriculumUnapprovedError,
)
from app.curriculum.importer import CurriculumImporter
from app.curriculum.models import ReviewStatus
from app.curriculum.service import CurriculumService
from app.persistence.database import get_engine, get_session_maker
from app.persistence.models import Base
from app.persistence.repositories import SessionRepository
from app.persistence.seed import seed_minimal_database


@pytest.fixture
async def seeded_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = get_session_maker(engine)
    async with session_maker() as session:
        await seed_minimal_database(session)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_service_retrieval_and_provenance(
    seeded_session: AsyncSession,
) -> None:
    """Acceptance Criterion 4: Retrieved items include content/version IDs and cache references."""
    # Import the full pilot pack as approved release
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "curriculum"
        / "pilot_body_parts_pack.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    importer = CurriculumImporter(seeded_session)
    await importer.import_manifest(data)

    service = CurriculumService(seeded_session)

    # 1. Retrieve single activity
    prov = await service.get_active_activity("curriculum-pilot-v1.0", "body_parts_mata")
    assert prov.curriculum_version_token == "curriculum-pilot-v1.0"
    assert prov.curriculum_status == ReviewStatus.APPROVED
    assert prov.approved_by == "dr_susanti_sp_a_paud_expert@toki.id"
    assert prov.item_token == "body_parts_mata"
    assert prov.skill_token == "body_parts"
    assert prov.module == "body_parts"
    assert prov.difficulty == 1
    assert "mata" in prov.answer_spec.exact_matches
    assert "kedua mata" in prov.answer_spec.synonyms
    assert prov.audio_refs.fallback_audio_id == "audio_fallback_mata_001"
    assert prov.audio_refs.prompt_audio_id == "audio_prompt_mata_001"
    assert len(prov.hints) == 2

    # 2. Retrieve by database item ID
    by_id = await service.get_activity_by_id(prov.item_id)
    assert by_id.item_id == prov.item_id
    assert by_id.item_token == "body_parts_mata"


@pytest.mark.asyncio
async def test_runtime_service_rejects_draft_and_revoked_content(
    seeded_session: AsyncSession,
) -> None:
    """Acceptance Criterion 2: Only approved active/pinned versions are served (FR-006)."""
    importer = CurriculumImporter(seeded_session)
    approval = CurriculumApprovalManager(seeded_session)
    service = CurriculumService(seeded_session)

    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "curriculum"
        / "pilot_body_parts_pack.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Import as DRAFT
    data["version_token"] = "curr-test-draft-v1.0"
    data["status"] = "DRAFT"
    await importer.import_manifest(data)

    # Rejection of DRAFT content in runtime session (FR-006)
    with pytest.raises(CurriculumUnapprovedError) as exc_info:
        await service.get_active_activity("curr-test-draft-v1.0", "body_parts_mata")
    assert "is DRAFT and cannot be accessed" in str(exc_info.value)

    # 2. Approve it -> Now it can be served
    await approval.approve_version("curr-test-draft-v1.0", "reviewer_001")
    prov = await service.get_active_activity("curr-test-draft-v1.0", "body_parts_mata")
    assert prov.curriculum_status == ReviewStatus.APPROVED

    # 3. Revoke it -> Now it is rejected (FR-006)
    await approval.revoke_version("curr-test-draft-v1.0", "Outdated", "reviewer_001")
    with pytest.raises(CurriculumRevokedError) as exc_info_rev:
        await service.get_active_activity("curr-test-draft-v1.0", "body_parts_mata")
    assert "is REVOKED and cannot be accessed" in str(exc_info_rev.value)


@pytest.mark.asyncio
async def test_runtime_service_session_pinned_version(
    seeded_session: AsyncSession,
) -> None:
    """Acceptance Criterion 2: Pinned curriculum version retrieved for active child session."""
    session_repo = SessionRepository(seeded_session)
    service = CurriculumService(seeded_session)

    # Create a session pinned to 'curr-v1.0' (from seed_minimal_database)
    sess = await session_repo.create_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
    )

    activities = await service.get_activities_for_session(sess.id)
    assert len(activities) >= 2
    tokens = [a.item_token for a in activities]
    assert "body_parts_mata" in tokens
    assert "body_parts_telinga" in tokens
    for a in activities:
        assert a.curriculum_version_id == "curr-v1.0"
        assert a.curriculum_status == ReviewStatus.APPROVED


@pytest.mark.asyncio
async def test_runtime_service_structured_filtering(
    seeded_session: AsyncSession,
) -> None:
    """Structured query filtering by module, skill, and difficulty (ADR-005)."""
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "curriculum"
        / "pilot_body_parts_pack.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    importer = CurriculumImporter(seeded_session)
    await importer.import_manifest(data)

    service = CurriculumService(seeded_session)

    # Filter difficulty 1 (Beginner)
    diff1_items = await service.query_activities(
        version_token="curriculum-pilot-v1.0",
        difficulty=1,
    )
    assert len(diff1_items) == 2
    assert {i.item_token for i in diff1_items} == {"body_parts_mata", "body_parts_hidung"}

    # Filter difficulty 2 (Intermediate)
    diff2_items = await service.query_activities(
        version_token="curriculum-pilot-v1.0",
        difficulty=2,
    )
    assert len(diff2_items) == 2
    assert {i.item_token for i in diff2_items} == {"body_parts_telinga", "body_parts_mulut"}

    # List approved versions
    approved_versions = await service.list_approved_versions()
    assert "curriculum-pilot-v1.0" in approved_versions
    assert "curriculum-v1.0" in approved_versions
