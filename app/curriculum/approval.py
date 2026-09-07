"""Curriculum approval lifecycle and immutability management (FR-006, DATA-003)."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.exceptions import (
    CurriculumError,
    CurriculumImmutabilityError,
    CurriculumNotFoundError,
)
from app.curriculum.models import ReviewStatus
from app.persistence.models import (
    CurriculumItem,
    CurriculumSkill,
    CurriculumVersion,
    utc_now,
)


class CurriculumApprovalManager:
    """Manages formal pedagogical review sign-off, revocation, and immutable version forking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_version(self, version_token: str) -> CurriculumVersion:
        """Fetch curriculum version by version token."""
        stmt = select(CurriculumVersion).where(CurriculumVersion.version_token == version_token)
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()
        if version is None:
            raise CurriculumNotFoundError(f"Curriculum version '{version_token}' not found")
        return version

    async def approve_version(self, version_token: str, reviewer_id: str) -> CurriculumVersion:
        """Formally approve and seal a curriculum version for production runtime use (DATA-003).

        After approval:
        - Version becomes immutable.
        - Runtime queries can safely serve activities from this release (FR-006).
        """
        version = await self.get_version(version_token)

        if version.status == ReviewStatus.APPROVED.value:
            # Idempotent if approved by same reviewer
            if version.approved_by == reviewer_id:
                return version
            raise CurriculumImmutabilityError(
                f"Version '{version_token}' is already APPROVED by '{version.approved_by}'"
            )

        if version.status in (ReviewStatus.REVOKED.value, ReviewStatus.ARCHIVED.value):
            raise CurriculumImmutabilityError(
                f"Cannot approve a {version.status} curriculum version '{version_token}'"
            )

        now = utc_now()
        version.status = ReviewStatus.APPROVED.value
        version.approved_by = reviewer_id
        version.approved_at = now
        await self.session.flush()
        return version

    async def revoke_version(
        self, version_token: str, reason: str, reviewer_id: str
    ) -> CurriculumVersion:
        """Revoke an approved curriculum version, halting further child sessions (FR-006)."""
        version = await self.get_version(version_token)
        version.status = ReviewStatus.REVOKED.value
        await self.session.flush()
        return version

    async def fork_new_version(
        self,
        source_version_token: str,
        new_version_token: str,
        created_by: str,
    ) -> CurriculumVersion:
        """Fork an approved or draft curriculum release into a new DRAFT version.

        Enforces DATA-003:
        Pedagogical edits must never mutate an approved release in-place.
        Instead, fork into a new version, edit, and submit for re-review.
        """
        source = await self.get_version(source_version_token)

        # Ensure new version token does not exist
        stmt = select(CurriculumVersion).where(CurriculumVersion.version_token == new_version_token)
        res = await self.session.execute(stmt)
        if res.scalar_one_or_none() is not None:
            raise CurriculumError(
                f"Cannot fork: target version '{new_version_token}' already exists"
            )

        now = utc_now()
        new_version = CurriculumVersion(
            id=str(uuid4()),
            version_token=new_version_token,
            status=ReviewStatus.DRAFT.value,
            approved_by=None,
            approved_at=None,
            created_at=now,
        )
        self.session.add(new_version)
        await self.session.flush()

        # Fetch all skills and items from source version
        skills_stmt = select(CurriculumSkill).where(
            CurriculumSkill.curriculum_version_id == source.id
        )
        skills_res = await self.session.execute(skills_stmt)
        source_skills = list(skills_res.scalars().all())

        skill_id_map: dict[str, str] = {}
        for s in source_skills:
            new_skill = CurriculumSkill(
                id=str(uuid4()),
                curriculum_version_id=new_version.id,
                skill_token=s.skill_token,
                name=s.name,
                domain=s.domain,
                target_age_band=s.target_age_band,
                created_at=now,
            )
            self.session.add(new_skill)
            skill_id_map[s.id] = new_skill.id

        await self.session.flush()

        items_stmt = select(CurriculumItem).where(CurriculumItem.curriculum_version_id == source.id)
        items_res = await self.session.execute(items_stmt)
        source_items = list(items_res.scalars().all())

        for itm in source_items:
            new_item = CurriculumItem(
                id=str(uuid4()),
                curriculum_version_id=new_version.id,
                skill_id=skill_id_map[itm.skill_id],
                item_token=itm.item_token,
                prompt_text=itm.prompt_text,
                expected_answers=itm.expected_answers,
                fallback_asset_id=itm.fallback_asset_id,
                activity_spec=dict(itm.activity_spec or {}),
                created_at=now,
            )
            self.session.add(new_item)

        await self.session.flush()
        return new_version
