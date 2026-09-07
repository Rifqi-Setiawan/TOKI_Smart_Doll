"""Immutable safety response catalog and trigger definitions.

(SEC-005, SEC-006, SEC-009, ADR-001)
"""

from dataclasses import dataclass
from enum import Enum

from app.contracts.device import DisplayState, GestureType
from app.contracts.response import PedagogicalAct


class SafetyCategory(str, Enum):
    """Categorization of child interaction safety concerns (SEC-006)."""

    DANGER = "DANGER"
    DISTRESS = "DISTRESS"
    EXPLICIT_STOP = "EXPLICIT_STOP"
    INAPPROPRIATE = "INAPPROPRIATE"


@dataclass(frozen=True)
class CannedSafetyResponse:
    """Immutable reviewed safety response metadata and cache references (SEC-005)."""

    response_id: str
    policy_id: str
    category: SafetyCategory
    approved_text: str
    audio_asset_id: str
    display: DisplayState
    gesture: GestureType
    pedagogical_act: PedagogicalAct
    is_escalation: bool
    requires_session_stop: bool


SAFETY_POLICY_VERSION = "SAFETY-POLICY-1.0"

# Initial reviewed Indonesian triggers for children ages 3-6 (SEC-006)
SAFETY_TRIGGER_KEYWORDS: dict[SafetyCategory, list[str]] = {
    SafetyCategory.DANGER: [
        "sakit",
        "darah",
        "api",
        "pisau",
        "gunting",
        "jatuh",
        "luka",
        "kebakaran",
        "tolong sakit",
    ],
    SafetyCategory.DISTRESS: [
        "takut",
        "seram",
        "nangis",
        "mama tolong",
        "papa tolong",
        "bunda tolong",
        "takut gelap",
    ],
    SafetyCategory.EXPLICIT_STOP: [
        "berhenti",
        "stop",
        "sudah",
        "selesai",
        "gak mau lagi",
        "tidak mau lagi",
        "mau udahan",
        "udahan",
    ],
    SafetyCategory.INAPPROPRIATE: [
        "pukul",
        "bunuh",
        "mati",
        "senjata",
        "tembak",
    ],
}

# Immutable canned safety responses (SEC-005, SEC-009)
CANNED_RESPONSES: dict[SafetyCategory, CannedSafetyResponse] = {
    SafetyCategory.DANGER: CannedSafetyResponse(
        response_id="canned-safe-danger-v1",
        policy_id=SAFETY_POLICY_VERSION,
        category=SafetyCategory.DANGER,
        approved_text="Toki ada di sini. Ayo istirahat dan beritahu orang tua ya.",
        audio_asset_id="audio-canned-safe-danger-01",
        display=DisplayState.SPEAKING,
        gesture=GestureType.RESET,
        pedagogical_act=PedagogicalAct.ESCALATION,
        is_escalation=True,
        requires_session_stop=True,
    ),
    SafetyCategory.DISTRESS: CannedSafetyResponse(
        response_id="canned-safe-distress-v1",
        policy_id=SAFETY_POLICY_VERSION,
        category=SafetyCategory.DISTRESS,
        approved_text="Tidak apa-apa sayang. Kita istirahat dulu ya, Toki temani.",
        audio_asset_id="audio-canned-safe-distress-01",
        display=DisplayState.ENCOURAGING,
        gesture=GestureType.NOD,
        pedagogical_act=PedagogicalAct.ESCALATION,
        is_escalation=True,
        requires_session_stop=True,
    ),
    SafetyCategory.EXPLICIT_STOP: CannedSafetyResponse(
        response_id="canned-safe-stop-v1",
        policy_id=SAFETY_POLICY_VERSION,
        category=SafetyCategory.EXPLICIT_STOP,
        approved_text="Bagus sekali bermainnya hari ini! Sampai jumpa lagi ya.",
        audio_asset_id="audio-canned-safe-stop-01",
        display=DisplayState.HAPPY,
        gesture=GestureType.WAVE,
        pedagogical_act=PedagogicalAct.CLOSING,
        is_escalation=False,
        requires_session_stop=True,
    ),
    SafetyCategory.INAPPROPRIATE: CannedSafetyResponse(
        response_id="canned-safe-inappropriate-v1",
        policy_id=SAFETY_POLICY_VERSION,
        category=SafetyCategory.INAPPROPRIATE,
        approved_text="Toki ingin kita bermain dengan ramah dan ceria ya.",
        audio_asset_id="audio-canned-safe-inappropriate-01",
        display=DisplayState.SPEAKING,
        gesture=GestureType.RESET,
        pedagogical_act=PedagogicalAct.ESCALATION,
        is_escalation=True,
        requires_session_stop=True,
    ),
}

# Generic fallback when activity template is missing or invalid (ADR-007)
GENERIC_SAFE_FALLBACK = CannedSafetyResponse(
    response_id="canned-generic-fallback-v1",
    policy_id=SAFETY_POLICY_VERSION,
    category=SafetyCategory.EXPLICIT_STOP,
    approved_text="Wah, hebat sudah mencoba! Ayo kita lanjutkan kegiatan berikutnya ya.",
    audio_asset_id="audio-canned-generic-fallback-01",
    display=DisplayState.ENCOURAGING,
    gesture=GestureType.NOD,
    pedagogical_act=PedagogicalAct.CORRECTIVE_FEEDBACK,
    is_escalation=False,
    requires_session_stop=False,
)
