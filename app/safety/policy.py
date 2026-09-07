"""Deterministic child interaction safety policy evaluator (SEC-005, SEC-006, SEC-009, FR-012)."""

from dataclasses import dataclass

from app.contracts.device import DeviceEvent, EventType
from app.safety.catalog import (
    CANNED_RESPONSES,
    SAFETY_POLICY_VERSION,
    SAFETY_TRIGGER_KEYWORDS,
    CannedSafetyResponse,
    SafetyCategory,
)
from app.understanding.normalization import extract_meaningful_tokens, normalize_text


@dataclass(frozen=True)
class SafetyEvaluation:
    """Outcome of safety policy inspection."""

    is_safe: bool
    category: SafetyCategory | None
    trigger_phrase: str | None
    canned_response: CannedSafetyResponse | None
    policy_id: str = SAFETY_POLICY_VERSION


class SafetyPolicyEvaluator:
    """Deterministic safety inspector enforcing immediate fail-closed overrides."""

    def __init__(self, policy_id: str = SAFETY_POLICY_VERSION) -> None:
        self.policy_id = policy_id

    def evaluate_text(self, text: str) -> SafetyEvaluation:
        """Inspect Indonesian child utterance for safety triggers."""
        normalized = normalize_text(text)
        if not normalized:
            return SafetyEvaluation(
                is_safe=True,
                category=None,
                trigger_phrase=None,
                canned_response=None,
                policy_id=self.policy_id,
            )

        tokens = set(extract_meaningful_tokens(normalized))

        # Priority order: DANGER > DISTRESS > INAPPROPRIATE > EXPLICIT_STOP
        check_order = [
            SafetyCategory.DANGER,
            SafetyCategory.DISTRESS,
            SafetyCategory.INAPPROPRIATE,
            SafetyCategory.EXPLICIT_STOP,
        ]

        for category in check_order:
            keywords = SAFETY_TRIGGER_KEYWORDS[category]
            for kw in keywords:
                norm_kw = normalize_text(kw)
                # Multi-word phrase check or single token match
                if " " in norm_kw:
                    if norm_kw in normalized:
                        return SafetyEvaluation(
                            is_safe=False,
                            category=category,
                            trigger_phrase=kw,
                            canned_response=CANNED_RESPONSES[category],
                            policy_id=self.policy_id,
                        )
                elif norm_kw in tokens:
                    return SafetyEvaluation(
                        is_safe=False,
                        category=category,
                        trigger_phrase=kw,
                        canned_response=CANNED_RESPONSES[category],
                        policy_id=self.policy_id,
                    )

        return SafetyEvaluation(
            is_safe=True,
            category=None,
            trigger_phrase=None,
            canned_response=None,
            policy_id=self.policy_id,
        )

    def evaluate_event(self, event: DeviceEvent | EventType) -> SafetyEvaluation:
        """Evaluate hardware/interaction event for emergency or guardian stop."""
        evt_type = event.event_type if isinstance(event, DeviceEvent) else event

        # Hardware button press acts as physical guardian/child stop action (SEC-009, FR-022)
        if evt_type == EventType.BUTTON_PRESSED:
            return SafetyEvaluation(
                is_safe=False,
                category=SafetyCategory.EXPLICIT_STOP,
                trigger_phrase="hardware_button_stop",
                canned_response=CANNED_RESPONSES[SafetyCategory.EXPLICIT_STOP],
                policy_id=self.policy_id,
            )

        return SafetyEvaluation(
            is_safe=True,
            category=None,
            trigger_phrase=None,
            canned_response=None,
            policy_id=self.policy_id,
        )
