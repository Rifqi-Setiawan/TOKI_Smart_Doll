"""Contract tests for typed errors and security redactions (API-005)."""

import json
from pathlib import Path

from app.contracts.errors import ErrorCode, ErrorResponse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_error_response_valid_fixture():
    """Valid error response fixture parses cleanly."""
    with open(FIXTURES_DIR / "error_response_valid.json", encoding="utf-8") as f:
        data = json.load(f)

    err = ErrorResponse.model_validate(data)
    assert err.error_code == ErrorCode.INVALID_PAYLOAD
    assert err.message == "Field 'seq' must be a positive integer"
    assert err.correlation_id == "corr-8832-ae"


def test_error_response_redacts_sensitive_keys():
    """API-005: Details containing secret tokens, keys, passwords, or stack traces are redacted."""
    raw_details = {
        "user_api_key": "sk-secret-12345",
        "nested": {
            "password": "my_db_password",
            "access_token": "bearer-xyz",
            "prompt_template": "System prompt instructions...",
            "traceback": "File app/main.py, line 20, in test",
        },
        "safe_field": "valid_value",
    }

    err = ErrorResponse(
        error_code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        correlation_id="corr-99",
        details=raw_details,
    )

    details = err.details
    assert details["user_api_key"] == "[REDACTED]"
    assert details["nested"]["password"] == "[REDACTED]"
    assert details["nested"]["access_token"] == "[REDACTED]"
    assert details["nested"]["prompt_template"] == "[REDACTED]"
    assert details["nested"]["traceback"] == "[REDACTED]"
    assert details["safe_field"] == "valid_value"
