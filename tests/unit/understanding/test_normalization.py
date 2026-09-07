"""Unit tests for Indonesian text normalization (FR-008, ADR-006)."""

from app.understanding.normalization import (
    compute_token_distance,
    extract_core_keywords,
    extract_meaningful_tokens,
    is_silence_or_empty,
    normalize_text,
    strip_accents_and_diacritics,
)


def test_strip_accents_and_diacritics() -> None:
    assert strip_accents_and_diacritics("Café") == "Cafe"
    assert strip_accents_and_diacritics("héllo wörld") == "hello world"
    assert strip_accents_and_diacritics("mata") == "mata"


def test_normalize_text_casing_and_punctuation() -> None:
    assert normalize_text("MATA!") == "mata"
    assert normalize_text("  Ini, Telinga?  ") == "ini telinga"
    assert normalize_text("Hidung... Toki.") == "hidung toki"
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""


def test_normalize_text_reduplication() -> None:
    assert normalize_text("mata-mata") == "mata mata"
    assert normalize_text("kuping_kuping") == "kuping kuping"


def test_is_silence_or_empty() -> None:
    assert is_silence_or_empty("") is True
    assert is_silence_or_empty("   ") is True
    assert is_silence_or_empty("...") is True
    assert is_silence_or_empty("eh") is True
    assert is_silence_or_empty("em anu uhm") is True
    assert is_silence_or_empty("mata") is False
    assert is_silence_or_empty("eh mata") is False


def test_extract_meaningful_tokens() -> None:
    assert extract_meaningful_tokens("eh anu mata") == ["mata"]
    assert extract_meaningful_tokens("emmm hidung toki") == ["hidung", "toki"]
    assert extract_meaningful_tokens("eh anu") == ["eh", "anu"]
    assert extract_meaningful_tokens("") == []


def test_extract_core_keywords() -> None:
    assert extract_core_keywords("ini mata toki") == ["mata", "toki"]
    assert extract_core_keywords("eh itu telinga ya") == ["telinga"]
    assert extract_core_keywords("dong kan") == ["dong", "kan"]


def test_compute_token_distance() -> None:
    assert compute_token_distance("mata", "mata") == 0
    assert compute_token_distance("hidung", "hidun") == 1
    assert compute_token_distance("telinga", "teliga") == 1
    assert compute_token_distance("kaki", "tangan") > 1
    assert compute_token_distance("", "abc") == 3
    assert compute_token_distance("abc", "") == 3
