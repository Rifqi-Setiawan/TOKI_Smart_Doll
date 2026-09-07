"""Understanding module containing normalization, deterministic assessor, and evaluation tools."""

from app.understanding.deterministic_assessor import DeterministicAssessor
from app.understanding.evaluator import (
    AssessmentMetrics,
    evaluate_labeled_cases,
    load_and_evaluate_fixtures,
)
from app.understanding.interfaces import SemanticResolver
from app.understanding.normalization import is_silence_or_empty, normalize_text

__all__ = [
    "AssessmentMetrics",
    "DeterministicAssessor",
    "SemanticResolver",
    "evaluate_labeled_cases",
    "is_silence_or_empty",
    "load_and_evaluate_fixtures",
    "normalize_text",
]
