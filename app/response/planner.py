"""Deterministic response planner selecting approved pedagogical templates and safety overrides.

(FR-010, FR-011, FR-012, FR-013, SEC-005, SEC-009, ADR-001, ADR-007, ADR-009)
"""

import uuid

from app.contracts.device import DisplayState, GestureType
from app.contracts.response import ContentProvenance, PedagogicalAct, ResponsePlan
from app.contracts.understanding import AssessmentResult, AssessmentStatus
from app.curriculum.models import ActivityProvenance, CurriculumActivity
from app.response.validators import validate_response_plan
from app.safety.catalog import (
    CANNED_RESPONSES,
    GENERIC_SAFE_FALLBACK,
    SafetyCategory,
)
from app.safety.policy import SafetyEvaluation, SafetyPolicyEvaluator


class ResponsePlanner:
    """Pure, deterministic response planner producing schema-valid ResponsePlans."""

    def __init__(
        self,
        safety_evaluator: SafetyPolicyEvaluator | None = None,
        default_curriculum_version: str = "curriculum-v1.0",
    ) -> None:
        self.safety_evaluator = safety_evaluator or SafetyPolicyEvaluator()
        self.default_curriculum_version = default_curriculum_version

    def plan_safe_stop(
        self,
        session_id: str,
        turn_id: str,
        curriculum_version: str | None = None,
    ) -> ResponsePlan:
        """Produce safe closing response plan without calling dynamic providers (SEC-009)."""
        canned = CANNED_RESPONSES[SafetyCategory.EXPLICIT_STOP]
        version = curriculum_version or self.default_curriculum_version

        plan = ResponsePlan(
            plan_id=f"plan-stop-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            turn_id=turn_id,
            pedagogical_act=canned.pedagogical_act,
            approved_text=canned.approved_text,
            spoken_text=canned.approved_text,
            audio_asset_id=canned.audio_asset_id,
            provenance=ContentProvenance(
                curriculum_version=version,
                module_id="system",
                activity_id="safe_stop",
                template_id=canned.response_id,
            ),
            display=canned.display,
            gesture=canned.gesture,
            is_escalation=canned.is_escalation,
            paraphrase_applied=False,
        )
        validate_response_plan(plan)
        return plan

    def plan_safety_override(
        self,
        session_id: str,
        turn_id: str,
        safety_eval: SafetyEvaluation,
        curriculum_version: str | None = None,
    ) -> ResponsePlan:
        """Produce immediate immutable safety escalation response (SEC-005, FR-012)."""
        canned = safety_eval.canned_response or CANNED_RESPONSES[SafetyCategory.DANGER]
        version = curriculum_version or self.default_curriculum_version

        plan = ResponsePlan(
            plan_id=f"plan-safety-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            turn_id=turn_id,
            pedagogical_act=canned.pedagogical_act,
            approved_text=canned.approved_text,
            spoken_text=canned.approved_text,
            audio_asset_id=canned.audio_asset_id,
            provenance=ContentProvenance(
                curriculum_version=version,
                module_id="safety",
                activity_id=f"safety_{canned.category.value.lower()}",
                template_id=canned.response_id,
            ),
            display=canned.display,
            gesture=canned.gesture,
            is_escalation=canned.is_escalation,
            paraphrase_applied=False,
        )
        validate_response_plan(plan)
        return plan

    def plan_generic_fallback(
        self,
        session_id: str,
        turn_id: str,
        curriculum_version: str | None = None,
        reason: str = "missing_activity_content",
    ) -> ResponsePlan:
        """Produce observable reviewed fallback when activity content is missing/corrupted."""
        canned = GENERIC_SAFE_FALLBACK
        version = curriculum_version or self.default_curriculum_version

        plan = ResponsePlan(
            plan_id=f"plan-fallback-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            turn_id=turn_id,
            pedagogical_act=canned.pedagogical_act,
            approved_text=canned.approved_text,
            spoken_text=canned.approved_text,
            audio_asset_id=canned.audio_asset_id,
            provenance=ContentProvenance(
                curriculum_version=version,
                module_id="fallback",
                activity_id=reason,
                template_id=canned.response_id,
            ),
            display=canned.display,
            gesture=canned.gesture,
            is_escalation=canned.is_escalation,
            paraphrase_applied=False,
        )
        validate_response_plan(plan)
        return plan

    def plan_response(
        self,
        session_id: str,
        turn_id: str,
        assessment: AssessmentResult,
        activity: CurriculumActivity | ActivityProvenance | None,
        turn_retry_count: int = 0,
        raw_transcript: str | None = None,
        safety_eval: SafetyEvaluation | None = None,
    ) -> ResponsePlan:
        """Compute the deterministic ResponsePlan for an assessment turn.

        Priority Order:
        1. High-severity safety trigger override (FR-012, SEC-005).
        2. Missing/corrupt activity fallback (ADR-007).
        3. Assessment status dispatch with bounded single retry (FR-010, FR-011).
        """
        # 1. High-Severity Safety Override (SEC-005, FR-012)
        eval_result = safety_eval
        if eval_result is None and raw_transcript:
            eval_result = self.safety_evaluator.evaluate_text(raw_transcript)

        if eval_result and not eval_result.is_safe:
            return self.plan_safety_override(
                session_id=session_id,
                turn_id=turn_id,
                safety_eval=eval_result,
            )

        # 2. Missing/Corrupted Activity Guard
        if activity is None:
            return self.plan_generic_fallback(
                session_id=session_id,
                turn_id=turn_id,
                reason="missing_activity",
            )

        # Extract activity parameters
        if isinstance(activity, ActivityProvenance):
            activity_id = activity.item_token
            module_id = activity.module
            audio_refs = activity.audio_refs
            hints = activity.hints
            retry_prompt = activity.retry_prompt
            answer_spec = activity.answer_spec
            curriculum_version = activity.curriculum_version_token
        else:
            activity_id = activity.activity_token
            module_id = activity.module
            audio_refs = activity.audio_refs
            hints = activity.hints
            retry_prompt = activity.retry_prompt
            answer_spec = activity.answer_spec
            curriculum_version = self.default_curriculum_version

        fallback_audio = audio_refs.fallback_audio_id
        prompt_audio = audio_refs.prompt_audio_id or fallback_audio
        hint_audios = audio_refs.hint_audio_ids

        # 3. Assessment Outcome Dispatch (FR-010, FR-011)
        status = assessment.status

        # Case A: CORRECT
        if status == AssessmentStatus.CORRECT:
            matched = assessment.matched_phrase or activity_id
            text = f"Pintar sekali! Jawabanmu benar, ini {matched}."
            template_id = "tpl-praise-exact"
            plan = ResponsePlan(
                plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                session_id=session_id,
                turn_id=turn_id,
                pedagogical_act=PedagogicalAct.PRAISE,
                approved_text=text,
                spoken_text=text,
                audio_asset_id=prompt_audio,
                provenance=ContentProvenance(
                    curriculum_version=curriculum_version,
                    module_id=module_id,
                    activity_id=activity_id,
                    template_id=template_id,
                ),
                display=DisplayState.HAPPY,
                gesture=GestureType.CELEBRATE,
                is_escalation=False,
                paraphrase_applied=False,
            )

        # Case B: INCORRECT
        elif status == AssessmentStatus.INCORRECT:
            if turn_retry_count < 1:
                # Bounded child-friendly single retry (FR-010)
                text = (
                    retry_prompt if retry_prompt else "Belum tepat sayang, ayo coba sekali lagi ya."
                )
                template_id = "tpl-retry-prompt"
                plan = ResponsePlan(
                    plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                    session_id=session_id,
                    turn_id=turn_id,
                    pedagogical_act=PedagogicalAct.RETRY_PROMPT,
                    approved_text=text,
                    spoken_text=text,
                    audio_asset_id=fallback_audio,
                    provenance=ContentProvenance(
                        curriculum_version=curriculum_version,
                        module_id=module_id,
                        activity_id=activity_id,
                        template_id=template_id,
                    ),
                    display=DisplayState.ENCOURAGING,
                    gesture=GestureType.TILT_HEAD,
                    is_escalation=False,
                    paraphrase_applied=False,
                )
            else:
                # Retry exhausted -> Bounded fallback (hint or revelation)
                if hints:
                    hint_text = hints[0]
                    audio_id = hint_audios[0] if hint_audios else fallback_audio
                    template_id = "tpl-hint-scaffold"
                    act = PedagogicalAct.HINT
                else:
                    target_name = (
                        answer_spec.exact_matches[0] if answer_spec.exact_matches else activity_id
                    )
                    hint_text = f"Tidak apa-apa! Yang benar adalah {target_name}."
                    audio_id = fallback_audio
                    template_id = "tpl-corrective-revelation"
                    act = PedagogicalAct.CORRECTIVE_FEEDBACK

                plan = ResponsePlan(
                    plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                    session_id=session_id,
                    turn_id=turn_id,
                    pedagogical_act=act,
                    approved_text=hint_text,
                    spoken_text=hint_text,
                    audio_asset_id=audio_id,
                    provenance=ContentProvenance(
                        curriculum_version=curriculum_version,
                        module_id=module_id,
                        activity_id=activity_id,
                        template_id=template_id,
                    ),
                    display=DisplayState.CURIOUS,
                    gesture=GestureType.NOD,
                    is_escalation=False,
                    paraphrase_applied=False,
                )

        # Case C: UNCERTAIN
        elif status == AssessmentStatus.UNCERTAIN:
            if turn_retry_count < 1:
                text = "Suaranya kurang jelas, ayo coba sebutkan lagi ya."
                template_id = "tpl-uncertain-retry"
                act = PedagogicalAct.RETRY_PROMPT
            else:
                text = hints[0] if hints else "Ayo dengarkan, Toki beri petunjuk ya."
                template_id = "tpl-uncertain-fallback"
                act = PedagogicalAct.HINT

            audio_id = (
                hint_audios[0] if (act == PedagogicalAct.HINT and hint_audios) else fallback_audio
            )
            plan = ResponsePlan(
                plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                session_id=session_id,
                turn_id=turn_id,
                pedagogical_act=act,
                approved_text=text,
                spoken_text=text,
                audio_asset_id=audio_id,
                provenance=ContentProvenance(
                    curriculum_version=curriculum_version,
                    module_id=module_id,
                    activity_id=activity_id,
                    template_id=template_id,
                ),
                display=DisplayState.ENCOURAGING
                if act == PedagogicalAct.RETRY_PROMPT
                else DisplayState.CURIOUS,
                gesture=GestureType.TILT_HEAD
                if act == PedagogicalAct.RETRY_PROMPT
                else GestureType.NOD,
                is_escalation=False,
                paraphrase_applied=False,
            )

        # Case D: NO_RESPONSE (silence / timeout)
        else:
            if turn_retry_count < 1:
                text = "Toki masih menunggu, ayo coba jawab ya."
                template_id = "tpl-no-speech-prompt"
                act = PedagogicalAct.RETRY_PROMPT
            else:
                text = hints[0] if hints else "Tidak apa-apa, ayo Toki beri petunjuk ya."
                template_id = "tpl-no-speech-fallback"
                act = PedagogicalAct.HINT

            audio_id = (
                hint_audios[0] if (act == PedagogicalAct.HINT and hint_audios) else fallback_audio
            )
            plan = ResponsePlan(
                plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                session_id=session_id,
                turn_id=turn_id,
                pedagogical_act=act,
                approved_text=text,
                spoken_text=text,
                audio_asset_id=audio_id,
                provenance=ContentProvenance(
                    curriculum_version=curriculum_version,
                    module_id=module_id,
                    activity_id=activity_id,
                    template_id=template_id,
                ),
                display=DisplayState.ENCOURAGING
                if act == PedagogicalAct.RETRY_PROMPT
                else DisplayState.CURIOUS,
                gesture=GestureType.TILT_HEAD
                if act == PedagogicalAct.RETRY_PROMPT
                else GestureType.NOD,
                is_escalation=False,
                paraphrase_applied=False,
            )

        validate_response_plan(plan)
        return plan
