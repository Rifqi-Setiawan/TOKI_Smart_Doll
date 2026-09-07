"""Deterministic answer assessor implementing pure rule-based evaluation.

(FR-008, FR-009, ADR-006)
"""

import time

from app.contracts.base import CallbackCorrelation
from app.contracts.speech import ASRResult, ASRStatus
from app.contracts.understanding import (
    AssessmentReasonCode,
    AssessmentResult,
    AssessmentStatus,
)
from app.curriculum.models import AnswerSpec
from app.understanding.normalization import (
    compute_token_distance,
    extract_core_keywords,
    extract_meaningful_tokens,
    is_silence_or_empty,
    normalize_text,
)


class DeterministicAssessor:
    """Evaluates child speech hypotheses against approved curriculum answers deterministically.

    Invariants (FR-009, ADR-006):
    - Exact, synonym, and common phonetic variants bypass expensive/probabilistic AI.
    - Low ASR confidence, silence, or audio errors are ALWAYS classified as system uncertainty
      (UNCERTAIN / NO_RESPONSE), NEVER as child incorrectness (INCORRECT).
    - Decisions are pure functions of inputs with deterministic repeatability.
    """

    def __init__(
        self,
        min_confidence: float = 0.65,
        policy_version: str = "RULE-ASSESS-1.0",
    ) -> None:
        self.min_confidence = min_confidence
        self.policy_version = policy_version

    def _match_phrase_in_tokens(self, phrase: str, tokens: list[str]) -> bool:
        """Check if multi-word phrase or single token appears in token stream."""
        norm_phrase = normalize_text(phrase)
        phrase_tokens = norm_phrase.split()
        if not phrase_tokens:
            return False

        p_len = len(phrase_tokens)
        t_len = len(tokens)
        if p_len > t_len:
            return False

        for i in range(t_len - p_len + 1):
            if tokens[i : i + p_len] == phrase_tokens:
                return True
        return False

    def _fuzzy_match_token(self, target_word: str, candidate_words: list[str]) -> str | None:
        """Find candidate word within edit distance threshold (<= 1 edit for word length >= 4)."""
        norm_target = normalize_text(target_word)
        t_len = len(norm_target)
        if t_len < 4:
            return None

        for cand in candidate_words:
            norm_cand = normalize_text(cand)
            if abs(len(norm_cand) - t_len) <= 1:
                dist = compute_token_distance(norm_target, norm_cand)
                if dist == 1:
                    return cand
        return None

    def assess(
        self,
        evidence: ASRResult | str,
        answer_spec: AnswerSpec | list[str],
        target_concept: str,
        correlation: CallbackCorrelation | None = None,
        custom_min_confidence: float | None = None,
    ) -> AssessmentResult:
        """Evaluate child answer evidence against curriculum answer specification."""
        start_time = time.perf_counter()

        # Extract correlation metadata
        session_id = correlation.session_id if correlation else "sess-local"
        turn_id = correlation.turn_id if correlation else "turn-0"
        state_version = correlation.state_version if correlation else 1

        # Normalize answer spec
        if isinstance(answer_spec, list):
            spec = AnswerSpec(exact_matches=answer_spec)
        else:
            spec = answer_spec

        threshold = (
            custom_min_confidence if custom_min_confidence is not None else self.min_confidence
        )

        # Extract transcript and confidence from evidence
        if isinstance(evidence, ASRResult):
            raw_transcript = evidence.transcript
            asr_status = evidence.status
            asr_confidence = evidence.confidence
        else:
            raw_transcript = str(evidence)
            asr_status = ASRStatus.SUCCESS
            asr_confidence = 1.0

        def make_result(
            status: AssessmentStatus,
            is_correct: bool,
            confidence: float,
            reason_code: AssessmentReasonCode,
            matched_phrase: str | None = None,
        ) -> AssessmentResult:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return AssessmentResult(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=status,
                target_concept=target_concept,
                matched_phrase=matched_phrase,
                is_correct=is_correct,
                confidence=confidence,
                reason_code=reason_code,
                policy_version=self.policy_version,
                evaluation_latency_ms=round(latency_ms, 2),
            )

        # 1. Audio Error / Timeout Guard (FR-009: Never INCORRECT)
        if asr_status in (ASRStatus.ERROR, ASRStatus.TIMEOUT):
            return make_result(
                status=AssessmentStatus.UNCERTAIN,
                is_correct=False,
                confidence=0.0,
                reason_code=AssessmentReasonCode.AUDIO_CORRUPTED,
            )

        # 2. Silence / No Speech Guard (FR-009: Never INCORRECT)
        if asr_status == ASRStatus.NO_SPEECH or is_silence_or_empty(raw_transcript):
            return make_result(
                status=AssessmentStatus.NO_RESPONSE,
                is_correct=False,
                confidence=1.0,
                reason_code=AssessmentReasonCode.NO_SPEECH_DETECTED,
            )

        # 3. Low Confidence Guard (FR-009: Low confidence is system uncertainty, not child error)
        if asr_confidence is not None and asr_confidence < threshold:
            return make_result(
                status=AssessmentStatus.UNCERTAIN,
                is_correct=False,
                confidence=asr_confidence,
                reason_code=AssessmentReasonCode.LOW_CONFIDENCE,
            )

        norm_transcript = normalize_text(raw_transcript)
        tokens = extract_meaningful_tokens(norm_transcript)
        core_tokens = extract_core_keywords(norm_transcript)

        # 4. Exact Match Rule
        for exact in spec.exact_matches:
            norm_exact = normalize_text(exact)
            if norm_transcript == norm_exact or self._match_phrase_in_tokens(norm_exact, tokens):
                return make_result(
                    status=AssessmentStatus.CORRECT,
                    is_correct=True,
                    confidence=1.0,
                    reason_code=AssessmentReasonCode.EXACT_MATCH,
                    matched_phrase=exact,
                )

        # 5. Approved Synonym Match Rule
        for syn in spec.synonyms:
            norm_syn = normalize_text(syn)
            if norm_transcript == norm_syn or self._match_phrase_in_tokens(norm_syn, tokens):
                return make_result(
                    status=AssessmentStatus.CORRECT,
                    is_correct=True,
                    confidence=0.95,
                    reason_code=AssessmentReasonCode.SYNONYM_MATCH,
                    matched_phrase=syn,
                )

        # 6. Toddler Phonetic / Variation Match Rule
        for p_var in spec.phonetic_variations:
            norm_pvar = normalize_text(p_var)
            if norm_transcript == norm_pvar or self._match_phrase_in_tokens(norm_pvar, tokens):
                return make_result(
                    status=AssessmentStatus.CORRECT,
                    is_correct=True,
                    confidence=0.90,
                    reason_code=AssessmentReasonCode.PHONETIC_MATCH,
                    matched_phrase=p_var,
                )

        # 7. Fuzzy Normalized Match Rule (Typo / slight slurring tolerance)
        for exact in spec.exact_matches:
            matched_word = self._fuzzy_match_token(exact, core_tokens)
            if matched_word:
                return make_result(
                    status=AssessmentStatus.CORRECT,
                    is_correct=True,
                    confidence=0.85,
                    reason_code=AssessmentReasonCode.NORMALIZED_MATCH,
                    matched_phrase=matched_word,
                )

        # 8. Explicit Mismatch Rule
        # If the child spoke a clear, high-confidence utterance that does not match
        confidence_val = asr_confidence if asr_confidence is not None else 0.85
        return make_result(
            status=AssessmentStatus.INCORRECT,
            is_correct=False,
            confidence=confidence_val,
            reason_code=AssessmentReasonCode.EXPLICIT_MISMATCH,
            matched_phrase=norm_transcript,
        )
