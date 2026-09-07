"""Deterministic seed fixtures for test and offline demo twin (ADR-014, DATA-007)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import (
    Child,
    ChildMastery,
    Consent,
    CurriculumItem,
    CurriculumSkill,
    CurriculumVersion,
    Device,
    Guardian,
    VersionMetadata,
    utc_now,
)


async def seed_minimal_database(session: AsyncSession) -> dict[str, str]:
    """Populate minimal deterministic test and demo twin records."""
    now = utc_now()

    # 1. Version metadata (DATA-007)
    version_items = [
        ("curriculum", "curriculum-v1.0", {"description": "Basic body parts and animals"}),
        ("model", "whisper-id-v1", {"architecture": "whisper-tiny-id", "quantized": True}),
        ("prompt", "prompt-template-v1", {"style": "scaffolding", "max_words": 25}),
        ("policy", "safety-strict-v1", {"fail_closed": True, "curriculum_restricted": True}),
        ("threshold", "asr-confidence-v1", {"min_confidence": 0.65}),
        ("firmware", "esp32-v1.0.0", {"codec": "OPUS", "sample_rate": 16000}),
        ("release", "toki-demo-m0", {"milestone": "M0", "baseline_status": "FROZEN"}),
    ]
    for comp, ver, manifest in version_items:
        session.add(
            VersionMetadata(
                id=f"vm-{comp}-{ver}",
                component=comp,
                version_token=ver,
                manifest=manifest,
                is_active=True,
                created_at=now,
            )
        )

    # 2. Approved curriculum version (DATA-003)
    curr_ver = CurriculumVersion(
        id="curr-v1.0",
        version_token="curriculum-v1.0",
        status="APPROVED",
        approved_by="pedagogy_reviewer@toki.id",
        approved_at=now,
        created_at=now,
    )
    session.add(curr_ver)

    skill = CurriculumSkill(
        id="skill-body-parts",
        curriculum_version_id=curr_ver.id,
        skill_token="body_parts",
        name="Mengenal Anggota Tubuh",
        domain="language",
        target_age_band="4-6",
        created_at=now,
    )
    session.add(skill)

    item1 = CurriculumItem(
        id="item-mata",
        curriculum_version_id=curr_ver.id,
        skill_id=skill.id,
        item_token="body_parts_mata",
        prompt_text="Coba sebutkan, bagian tubuh apa yang kita gunakan untuk melihat?",
        expected_answers=["mata"],
        fallback_asset_id="audio_item_mata_001",
        created_at=now,
    )
    item2 = CurriculumItem(
        id="item-telinga",
        curriculum_version_id=curr_ver.id,
        skill_id=skill.id,
        item_token="body_parts_telinga",
        prompt_text="Kalau yang kita gunakan untuk mendengar suara, namanya apa?",
        expected_answers=["telinga", "kuping"],
        fallback_asset_id="audio_item_telinga_001",
        created_at=now,
    )
    session.add_all([item1, item2])

    # 3. Guardian & Pseudonymous Child (DATA-008)
    guardian = Guardian(
        id="guard-demo-001",
        pseudonym="Bunda Rina",
        email_hash="hash_bunda_rina_demo_789abc",
        created_at=now,
    )
    session.add(guardian)

    child = Child(
        id="child-demo-001",
        guardian_id=guardian.id,
        pseudonym="Adik Bintang",
        age_band="4-5",
        created_at=now,
    )
    session.add(child)

    # 4. Device registration
    device = Device(
        id="dev-demo-001",
        device_serial="TOKI-DEMO-001",
        guardian_id=guardian.id,
        child_id=child.id,
        firmware_version="1.0.0",
        is_active=True,
        registered_at=now,
        last_seen_at=now,
    )
    session.add(device)

    # 5. Guardian Consent (DATA-010)
    consent = Consent(
        id="consent-demo-001",
        guardian_id=guardian.id,
        child_id=child.id,
        consent_type="DATA_PROCESSING",
        status="GRANTED",
        granted_at=now,
    )
    session.add(consent)

    # 6. Initial Mastery Baseline
    mastery = ChildMastery(
        id="mastery-demo-001",
        child_id=child.id,
        skill_token="body_parts",
        mastery_band="INTRODUCED",
        practice_count=0,
        success_count=0,
        last_attempt_at=None,
    )
    session.add(mastery)

    await session.flush()
    return {
        "guardian_id": guardian.id,
        "child_id": child.id,
        "device_id": device.id,
        "device_serial": device.device_serial,
        "curriculum_version_id": curr_ver.id,
        "curriculum_version_token": curr_ver.version_token,
    }
