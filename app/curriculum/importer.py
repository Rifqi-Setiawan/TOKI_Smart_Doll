"""Idempotent curriculum importer with field-level validation (FR-007, DATA-003)."""

from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.exceptions import (
    CurriculumImmutabilityError,
    CurriculumValidationError,
)
from app.curriculum.models import (
    CurriculumManifest,
    ReviewStatus,
)
from app.persistence.models import (
    CurriculumItem,
    CurriculumSkill,
    CurriculumVersion,
    utc_now,
)


class CurriculumImporter:
    """Validates and idempotently imports curriculum releases into authoritative persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def validate_manifest(
        self, data: dict[str, Any] | CurriculumManifest
    ) -> tuple[bool, list[str]]:
        """Perform comprehensive field-level validation on a curriculum package manifest."""
        errors: list[str] = []

        if isinstance(data, CurriculumManifest):
            manifest_dict = data.model_dump()
        elif isinstance(data, dict):
            manifest_dict = data
        else:
            return False, ["Input must be a dict or CurriculumManifest instance"]

        # 1. Manifest header checks
        version_token = manifest_dict.get("version_token")
        if not version_token or not str(version_token).strip():
            errors.append("manifest.version_token: Field is required and cannot be empty")

        description = manifest_dict.get("description")
        if not description or not str(description).strip():
            errors.append("manifest.description: Field is required and cannot be empty")

        # 2. Activities checks
        activities = manifest_dict.get("activities", [])
        if not activities or not isinstance(activities, list):
            errors.append("manifest.activities: Package must contain at least one activity")
        else:
            activity_tokens: set[str] = set()
            for idx, act in enumerate(activities):
                act_prefix = f"activities[{idx}]"
                token = act.get("activity_token")
                if not token or not str(token).strip():
                    errors.append(f"{act_prefix}.activity_token: Field is required")
                elif token in activity_tokens:
                    errors.append(
                        f"{act_prefix}.activity_token: Duplicate token '{token}' in package"
                    )
                else:
                    activity_tokens.add(token)

                module = act.get("module")
                if not module or not str(module).strip():
                    errors.append(f"{act_prefix}.module: Field is required")

                skill_token = act.get("skill_token")
                if not skill_token or not str(skill_token).strip():
                    errors.append(f"{act_prefix}.skill_token: Field is required")

                prompt = act.get("prompt_text")
                if not prompt or len(str(prompt).strip()) < 5:
                    errors.append(f"{act_prefix}.prompt_text: Must be at least 5 characters")

                # Answer spec check
                answer_spec = act.get("answer_spec", {})
                exact_matches = answer_spec.get("exact_matches", [])
                if not exact_matches or not isinstance(exact_matches, list):
                    errors.append(f"{act_prefix}.answer_spec.exact_matches: Missing expected match")

                # Audio references check
                audio_refs = act.get("audio_refs", {})
                fallback_id = audio_refs.get("fallback_audio_id")
                if not fallback_id or not str(fallback_id).strip():
                    errors.append(
                        f"{act_prefix}.audio_refs.fallback_audio_id: Fallback audio ID is mandatory"
                    )

        # 3. Pydantic validation roundtrip
        if not errors:
            try:
                CurriculumManifest.model_validate(manifest_dict)
            except Exception as exc:
                errors.append(f"Schema validation error: {exc}")

        return len(errors) == 0, errors

    async def import_manifest(self, data: dict[str, Any] | CurriculumManifest) -> CurriculumVersion:
        """Idempotently import curriculum manifest into PostgreSQL/SQLite.

        Enforces:
        - Strict pre-import validation reporting field-level errors (FR-007).
        - Rejection of overwriting or re-importing APPROVED curriculum versions (DATA-003).
        - Safe replacement of DRAFT versions for rapid iteration before formal sign-off.
        """
        is_valid, errors = self.validate_manifest(data)
        if not is_valid:
            raise CurriculumValidationError(
                f"Curriculum manifest validation failed with {len(errors)} error(s)",
                errors=errors,
            )

        if isinstance(data, CurriculumManifest):
            manifest = data
        else:
            manifest = CurriculumManifest.model_validate(data)
        version_token = manifest.version_token

        # Check existing version
        stmt = select(CurriculumVersion).where(CurriculumVersion.version_token == version_token)
        result = await self.session.execute(stmt)
        existing_version = result.scalar_one_or_none()

        now = utc_now()

        if existing_version is not None:
            if existing_version.status == ReviewStatus.APPROVED.value:
                raise CurriculumImmutabilityError(
                    f"DATA-003 violation: Version '{version_token}' is APPROVED and immutable. "
                    "Edits must create a new version with qualified reviewer audit trail."
                )
            if existing_version.status in (ReviewStatus.REVOKED.value, ReviewStatus.ARCHIVED.value):
                st = existing_version.status
                raise CurriculumImmutabilityError(
                    f"Version '{version_token}' is {st} and cannot be modified."
                )

            # Version is DRAFT: clean up existing child skills/items and re-populate (idempotent)
            version_record = existing_version
            version_record.created_at = now
            del_items = delete(CurriculumItem).where(
                CurriculumItem.curriculum_version_id == version_record.id
            )
            await self.session.execute(del_items)
            del_skills = delete(CurriculumSkill).where(
                CurriculumSkill.curriculum_version_id == version_record.id
            )
            await self.session.execute(del_skills)
            await self.session.flush()
        else:
            version_record = CurriculumVersion(
                id=str(uuid4()),
                version_token=version_token,
                status=manifest.status.value,
                approved_by=manifest.reviewed_by,
                approved_at=now if manifest.status == ReviewStatus.APPROVED else None,
                created_at=now,
            )
            self.session.add(version_record)
            await self.session.flush()

        # Build map of skills
        skill_map: dict[str, CurriculumSkill] = {}
        for skill_def in manifest.skills:
            skill = CurriculumSkill(
                id=str(uuid4()),
                curriculum_version_id=version_record.id,
                skill_token=skill_def.skill_token,
                name=skill_def.name,
                domain=skill_def.domain,
                target_age_band=skill_def.target_age_band,
                created_at=now,
            )
            self.session.add(skill)
            skill_map[skill_def.skill_token] = skill

        # Auto-create any skill referenced by activities that wasn't in skills list
        for act in manifest.activities:
            if act.skill_token not in skill_map:
                skill = CurriculumSkill(
                    id=str(uuid4()),
                    curriculum_version_id=version_record.id,
                    skill_token=act.skill_token,
                    name=act.skill_token.replace("_", " ").title(),
                    domain=act.module,
                    target_age_band=manifest.target_age_band,
                    created_at=now,
                )
                self.session.add(skill)
                skill_map[act.skill_token] = skill

        await self.session.flush()

        # Insert items
        for act in manifest.activities:
            skill = skill_map[act.skill_token]
            activity_payload = {
                "module": act.module,
                "difficulty": act.difficulty.value,
                "hints": act.hints,
                "retry_prompt": act.retry_prompt,
                "prompt_audio_id": act.audio_refs.prompt_audio_id,
                "hint_audio_ids": act.audio_refs.hint_audio_ids,
                "answer_spec": act.answer_spec.model_dump(),
                "review_notes": act.review_notes,
            }
            item = CurriculumItem(
                id=str(uuid4()),
                curriculum_version_id=version_record.id,
                skill_id=skill.id,
                item_token=act.activity_token,
                prompt_text=act.prompt_text,
                expected_answers=act.answer_spec.exact_matches,
                fallback_asset_id=act.audio_refs.fallback_audio_id,
                activity_spec=activity_payload,
                created_at=now,
            )
            self.session.add(item)

        await self.session.flush()
        return version_record
