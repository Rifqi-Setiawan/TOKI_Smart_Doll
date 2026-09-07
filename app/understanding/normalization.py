"""Deterministic Indonesian text normalization for child speech understanding (FR-008, ADR-006)."""

import re
import unicodedata

# Common Indonesian toddler speech hesitation particles and fillers
INDONESIAN_FILLERS = {
    "eh",
    "em",
    "emm",
    "emmm",
    "uh",
    "uhm",
    "umm",
    "ummm",
    "anu",
    "ehm",
    "he",
    "ha",
    "aa",
    "aaa",
}

# Discourse markers often prepended or appended in natural speech
DISCOURSE_MARKERS = {
    "itu",
    "ini",
    "kan",
    "ya",
    "iya",
    "dong",
    "sih",
    "tuh",
    "kok",
    "lah",
    "deh",
    "lho",
    "tadi",
    "aku",
    "saya",
    "namanya",
}


def strip_accents_and_diacritics(text: str) -> str:
    """Normalize unicode and strip diacritical marks."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_text(text: str) -> str:
    """Clean and normalize Indonesian child speech transcript.

    Operations:
    1. Lowercase and strip whitespace.
    2. Normalize Unicode diacritics.
    3. Remove punctuation (commas, periods, exclamation/question marks, quotes).
    4. Collapse multiple spaces into single space.
    5. Handle hyphenated Indonesian reduplication (e.g. 'mata-mata' -> 'mata mata').
    """
    if not text:
        return ""

    lowered = text.lower().strip()
    lowered = strip_accents_and_diacritics(lowered)

    # Replace hyphens with space to separate reduplicated or stuttered words
    lowered = re.sub(r"[-_]+", " ", lowered)

    # Remove all non-alphanumeric characters except spaces
    cleaned = re.sub(r"[^\w\s]", "", lowered)

    # Collapse multiple whitespaces
    collapsed = re.sub(r"\s+", " ", cleaned).strip()
    return collapsed


def is_silence_or_empty(text: str) -> bool:
    """Check if transcript is effectively silent, empty, or purely non-lexical noise."""
    normalized = normalize_text(text)
    if not normalized:
        return True

    tokens = normalized.split()
    return all(tok in INDONESIAN_FILLERS for tok in tokens)


def extract_meaningful_tokens(text: str) -> list[str]:
    """Extract ordered list of meaningful lexical tokens, stripping non-lexical fillers."""
    normalized = normalize_text(text)
    if not normalized:
        return []

    tokens = normalized.split()
    filtered = [t for t in tokens if t not in INDONESIAN_FILLERS]
    return filtered if filtered else tokens


def extract_core_keywords(text: str) -> list[str]:
    """Extract content words by removing both fillers and common introductory discourse markers."""
    tokens = extract_meaningful_tokens(text)
    meaningful = [t for t in tokens if t not in DISCOURSE_MARKERS]
    return meaningful if meaningful else tokens


def compute_token_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0 = list(v1)

    return v1[len(s2)]
