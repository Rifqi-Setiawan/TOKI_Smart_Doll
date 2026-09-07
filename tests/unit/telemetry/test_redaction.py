"""Unit tests for privacy scanning and redaction rules (SEC-007, ADR-013)."""

from app.telemetry.redaction import (
    redact_sensitive_payload,
    scan_for_privacy_violations,
)


def test_clean_trace_payload_reports_zero_critical_findings() -> None:
    """SEC-007: Valid, compliant telemetry payloads must report zero privacy findings."""
    clean_payload = {
        "session_id": "sess-clean-01",
        "turn_id": "turn-clean-01",
        "turn_number": 1,
        "item_token": "item.colors.red",
        "spoken_text": "Bagus sekali, kamu hebat!",
        "audio_asset_id": "audio-asset-praise-01",
        "is_correct": True,
        "latency_ms": 42.5,
    }

    violations = scan_for_privacy_violations(clean_payload)
    assert violations == []


def test_redaction_scrubs_secrets_and_pii_and_media() -> None:
    """SEC-007: Direct secrets, emails, phones, and raw media are detected and scrubbed."""
    dirty_payload = {
        "user_token": "sk-1234567890abcdef1234567890",
        "auth_header": "Bearer secret_jwt_token_12345=",
        "full_name": "Adit Pratama",
        "email": "guardian.test@example.com",
        "phone": "081234567890",
        "raw_audio": "data:audio/wav;base64," + "A" * 120,
        "metadata": {
            "api_key": "secret-key-xyz",
            "safe_field": "Mengenal Warna",
        },
    }

    # 1. Scan detects violations
    initial_violations = scan_for_privacy_violations(dirty_payload)
    assert len(initial_violations) > 0

    # 2. Scrub payload
    scrubbed = redact_sensitive_payload(dirty_payload)

    assert scrubbed["user_token"] == "[REDACTED_SECRET]"
    assert "[REDACTED_SECRET]" in scrubbed["auth_header"]
    assert scrubbed["full_name"] == "[REDACTED_PII]"
    assert scrubbed["email"] == "[REDACTED_PII]"
    assert scrubbed["phone"] == "[REDACTED_PII]"
    assert scrubbed["raw_audio"] == "[REDACTED_MEDIA]"
    assert scrubbed["metadata"]["api_key"] == "[REDACTED_SECRET]"
    assert scrubbed["metadata"]["safe_field"] == "Mengenal Warna"

    # 3. Post-redaction scan reports ZERO critical findings
    post_scrub_violations = scan_for_privacy_violations(scrubbed)
    assert post_scrub_violations == []
