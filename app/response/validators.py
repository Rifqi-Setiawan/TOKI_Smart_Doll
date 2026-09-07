"""Response plan validators ensuring schema, word limit, provenance, and safety invariants.

(FR-011, AI-008, SEC-010, ADR-007)
"""

from app.contracts.response import PedagogicalAct, ResponsePlan

FORBIDDEN_CLINICAL_WORDS = {
    "terapi",
    "diagnosis",
    "autisme",
    "adhd",
    "depresi",
    "gangguan",
    "pasien",
    "klinis",
    "obat",
    "penyakit",
    "gejala",
}


class ResponsePlanValidationError(ValueError):
    """Raised when a ResponsePlan violates safety or schema constraints."""

    pass


def validate_response_plan(plan: ResponsePlan) -> None:
    """Validate a ResponsePlan against safety and architectural constraints.

    Invariants:
    - Maximum 25 spoken words for children 3-6 (AI-008).
    - Audio asset reference must not be blank (ADR-009).
    - Provenance must be fully specified (FR-011).
    - Clinical/diagnostic claims are strictly forbidden (SEC-010, ADR-001).
    - Escalation plans must have consistent flags and pedagogical acts (FR-012).
    """
    # 1. Non-blank text validation
    spoken_text = plan.spoken_text.strip()
    if not spoken_text:
        raise ResponsePlanValidationError("Spoken text cannot be blank")

    # 2. Word count limit (AI-008)
    words = spoken_text.split()
    if len(words) > 25:
        raise ResponsePlanValidationError(
            f"AI-008 violation: Spoken text has {len(words)} words, exceeding max 25 words"
        )

    # 3. Audio asset ID validation (ADR-009)
    if not plan.audio_asset_id or not plan.audio_asset_id.strip():
        raise ResponsePlanValidationError("ADR-009 violation: audio_asset_id cannot be blank")

    # 4. Provenance audit validation (FR-011)
    prov = plan.provenance
    if not prov.curriculum_version or not prov.activity_id or not prov.template_id:
        raise ResponsePlanValidationError(
            "FR-011 violation: Provenance must specify curriculum_version, activity_id, and "
            "template_id"
        )

    # 5. Non-clinical / non-diagnostic check (SEC-010, ADR-001)
    lowered_tokens = set(spoken_text.lower().replace(",", "").replace(".", "").split())
    clinical_intersection = lowered_tokens.intersection(FORBIDDEN_CLINICAL_WORDS)
    if clinical_intersection:
        raise ResponsePlanValidationError(
            f"SEC-010 violation: Forbidden clinical words: {clinical_intersection}"
        )

    # 6. Escalation flag consistency
    if plan.is_escalation and plan.pedagogical_act not in (
        PedagogicalAct.ESCALATION,
        PedagogicalAct.CLOSING,
    ):
        raise ResponsePlanValidationError(
            f"Inconsistent plan: is_escalation is True but act is {plan.pedagogical_act}"
        )
