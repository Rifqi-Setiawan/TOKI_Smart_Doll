"""Runtime curriculum query and access service with exact provenance (FR-006, ADR-005, DATA-007)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.curriculum.exceptions import (
    CurriculumNotFoundError,
    CurriculumRevokedError,
    CurriculumUnapprovedError,
)
from app.curriculum.models import (
    ActivityAudioReferences,
    ActivityProvenance,
    AnswerSpec,
    ReviewStatus,
)
from app.persistence.models import (
    CurriculumItem,
    CurriculumSkill,
    CurriculumVersion,
    Session,
)


class CurriculumService:
    """Indexed retrieval of approved pedagogical content for runtime sessions (ADR-005)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _build_provenance(
        self,
        version: CurriculumVersion,
        skill: CurriculumSkill,
        item: CurriculumItem,
    ) -> ActivityProvenance:
        """Construct immutable activity provenance record from database entities."""
        spec = dict(item.activity_spec or {})

        # Reconstruct AnswerSpec
        raw_answer_spec = spec.get("answer_spec")
        if raw_answer_spec and isinstance(raw_answer_spec, dict):
            answer_spec = AnswerSpec.model_validate(raw_answer_spec)
        else:
            answer_spec = AnswerSpec(exact_matches=item.expected_answers)

        # Reconstruct ActivityAudioReferences
        audio_refs = ActivityAudioReferences(
            prompt_audio_id=spec.get("prompt_audio_id"),
            fallback_audio_id=item.fallback_asset_id,
            hint_audio_ids=spec.get("hint_audio_ids", []),
        )

        return ActivityProvenance(
            curriculum_version_token=version.version_token,
            curriculum_version_id=version.id,
            curriculum_status=ReviewStatus(version.status),
            approved_by=version.approved_by,
            approved_at=version.approved_at.isoformat() if version.approved_at else None,
            item_id=item.id,
            item_token=item.item_token,
            skill_id=skill.id,
            skill_token=skill.skill_token,
            skill_name=skill.name,
            module=spec.get("module", skill.domain),
            difficulty=int(spec.get("difficulty", 1)),
            prompt_text=item.prompt_text,
            answer_spec=answer_spec,
            hints=spec.get("hints", []),
            retry_prompt=spec.get("retry_prompt"),
            audio_refs=audio_refs,
        )

    def _verify_version_approved(self, version: CurriculumVersion) -> None:
        """Enforce FR-006: only APPROVED content can enter child sessions."""
        if version.status == ReviewStatus.DRAFT.value:
            raise CurriculumUnapprovedError(
                f"FR-006 violation: Curriculum version '{version.version_token}' is DRAFT "
                "and cannot be accessed in a child session."
            )
        if version.status in (ReviewStatus.REVOKED.value, ReviewStatus.ARCHIVED.value):
            raise CurriculumRevokedError(
                f"FR-006 violation: Version '{version.version_token}' is {version.status} "
                "and cannot be accessed."
            )

    async def get_active_activity(self, version_token: str, item_token: str) -> ActivityProvenance:
        """Retrieve a specific approved activity turn by version and item token (FR-006, FR-007)."""
        stmt = (
            select(CurriculumItem)
            .join(CurriculumVersion, CurriculumItem.curriculum_version_id == CurriculumVersion.id)
            .join(CurriculumSkill, CurriculumItem.skill_id == CurriculumSkill.id)
            .where(
                CurriculumVersion.version_token == version_token,
                CurriculumItem.item_token == item_token,
            )
            .options(
                selectinload(CurriculumItem.curriculum_version),
                selectinload(CurriculumItem.skill),
            )
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            # Check if version exists to give a specific error
            ver_stmt = select(CurriculumVersion).where(
                CurriculumVersion.version_token == version_token
            )
            ver_res = await self.session.execute(ver_stmt)
            ver = ver_res.scalar_one_or_none()
            if ver is None:
                raise CurriculumNotFoundError(f"Curriculum version '{version_token}' not found")
            self._verify_version_approved(ver)
            raise CurriculumNotFoundError(
                f"Activity '{item_token}' not found in curriculum version '{version_token}'"
            )

        self._verify_version_approved(item.curriculum_version)
        return self._build_provenance(item.curriculum_version, item.skill, item)

    async def get_activity_by_id(self, item_id: str) -> ActivityProvenance:
        """Retrieve a specific activity by database item ID with approval enforcement."""
        stmt = (
            select(CurriculumItem)
            .where(CurriculumItem.id == item_id)
            .options(
                selectinload(CurriculumItem.curriculum_version),
                selectinload(CurriculumItem.skill),
            )
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            raise CurriculumNotFoundError(f"Curriculum item id '{item_id}' not found")

        self._verify_version_approved(item.curriculum_version)
        return self._build_provenance(item.curriculum_version, item.skill, item)

    async def get_activities_for_session(self, session_id: str) -> list[ActivityProvenance]:
        """Retrieve approved activities for an active session using its pinned version."""
        sess_stmt = select(Session).where(Session.id == session_id)
        sess_res = await self.session.execute(sess_stmt)
        sess = sess_res.scalar_one_or_none()
        if sess is None:
            raise CurriculumNotFoundError(f"Session '{session_id}' not found")

        ver_stmt = select(CurriculumVersion).where(
            CurriculumVersion.id == sess.curriculum_version_id
        )
        ver_res = await self.session.execute(ver_stmt)
        version = ver_res.scalar_one_or_none()
        if version is None:
            raise CurriculumNotFoundError(
                f"Pinned curriculum version '{sess.curriculum_version_id}' for session not found"
            )

        self._verify_version_approved(version)

        items_stmt = (
            select(CurriculumItem)
            .where(CurriculumItem.curriculum_version_id == version.id)
            .options(selectinload(CurriculumItem.skill))
        )
        items_res = await self.session.execute(items_stmt)
        items = list(items_res.scalars().all())

        return [self._build_provenance(version, itm.skill, itm) for itm in items]

    async def query_activities(
        self,
        version_token: str,
        module: str | None = None,
        skill_token: str | None = None,
        difficulty: int | None = None,
    ) -> list[ActivityProvenance]:
        """Structured PostgreSQL query filtering activities by pedagogical criteria (ADR-005)."""
        ver_stmt = select(CurriculumVersion).where(CurriculumVersion.version_token == version_token)
        ver_res = await self.session.execute(ver_stmt)
        version = ver_res.scalar_one_or_none()
        if version is None:
            raise CurriculumNotFoundError(f"Curriculum version '{version_token}' not found")

        self._verify_version_approved(version)

        stmt = (
            select(CurriculumItem)
            .join(CurriculumSkill, CurriculumItem.skill_id == CurriculumSkill.id)
            .where(CurriculumItem.curriculum_version_id == version.id)
            .options(selectinload(CurriculumItem.skill))
        )
        if skill_token is not None:
            stmt = stmt.where(CurriculumSkill.skill_token == skill_token)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        provenance_list: list[ActivityProvenance] = []
        for itm in items:
            prov = self._build_provenance(version, itm.skill, itm)
            if module is not None and prov.module != module:
                continue
            if difficulty is not None and prov.difficulty != difficulty:
                continue
            provenance_list.append(prov)

        return provenance_list

    async def list_approved_versions(self) -> list[str]:
        """List version tokens of all currently approved releases."""
        stmt = select(CurriculumVersion.version_token).where(
            CurriculumVersion.status == ReviewStatus.APPROVED.value
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
