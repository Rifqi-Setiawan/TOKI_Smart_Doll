"""Privacy scanning and redaction rules for logs, traces, and metrics (SEC-007, ADR-013)."""

import re
from typing import Any

# SEC-007: Forbidden secret and token patterns
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE),
    re.compile(r"(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?([^'\"\s]+)", re.IGNORECASE),
]

# PII Patterns: Email, Indonesian Phone Numbers, Direct NIK
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_PATTERN = re.compile(r"\b(\+?62|0)8[1-9][0-9]{7,10}\b")
RAW_BASE64_MEDIA_PATTERN = re.compile(r"data:audio/[a-z]+;base64,[A-Za-z0-9+/=]{100,}")

FORBIDDEN_PII_KEYS = {
    "full_name",
    "child_name",
    "email",
    "phone",
    "phone_number",
    "date_of_birth",
    "address",
    "nik",
}

FORBIDDEN_MEDIA_KEYS = {
    "raw_audio",
    "audio_bytes",
    "pcm_bytes",
    "raw_image",
    "camera_bytes",
}


def redact_sensitive_payload(data: Any) -> Any:
    """Recursively scrub raw media, secrets, and direct child PII from telemetry dictionaries."""
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if key_lower in FORBIDDEN_PII_KEYS:
                scrubbed[k] = "[REDACTED_PII]"
            elif key_lower in FORBIDDEN_MEDIA_KEYS:
                scrubbed[k] = "[REDACTED_MEDIA]"
            elif any(s in key_lower for s in ("secret", "password", "api_key", "token")):
                scrubbed[k] = "[REDACTED_SECRET]"
            else:
                scrubbed[k] = redact_sensitive_payload(v)
        return scrubbed

    if isinstance(data, list):
        return [redact_sensitive_payload(item) for item in data]

    if isinstance(data, str):
        text = data
        for pattern in SECRET_PATTERNS:
            text = pattern.sub("[REDACTED_SECRET]", text)
        text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
        text = RAW_BASE64_MEDIA_PATTERN.sub("[REDACTED_MEDIA]", text)
        return text

    return data


def scan_for_privacy_violations(data: Any) -> list[str]:
    """Scan payload for sensitive secrets, raw media, or direct child identifiers.

    Returns a list of violation descriptions. A compliant payload returns an empty list.
    """
    violations: list[str] = []

    def _scan(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                curr_path = f"{path}.{k}" if path else str(k)
                key_lower = str(k).lower()
                if key_lower in FORBIDDEN_PII_KEYS and v != "[REDACTED_PII]":
                    violations.append(f"PII key found at '{curr_path}': {k}")
                if key_lower in FORBIDDEN_MEDIA_KEYS and v != "[REDACTED_MEDIA]":
                    violations.append(f"Raw media key found at '{curr_path}': {k}")
                _scan(v, curr_path)

        elif isinstance(node, list):
            for i, item in enumerate(node):
                _scan(item, f"{path}[{i}]")

        elif isinstance(node, str):
            for pattern in SECRET_PATTERNS:
                if pattern.search(node):
                    violations.append(f"Secret pattern match at '{path}'")
            if EMAIL_PATTERN.search(node):
                violations.append(f"Email pattern match at '{path}'")
            if PHONE_PATTERN.search(node):
                violations.append(f"Phone number pattern match at '{path}'")
            if RAW_BASE64_MEDIA_PATTERN.search(node):
                violations.append(f"Raw audio/media payload match at '{path}'")

    _scan(data)
    return violations
