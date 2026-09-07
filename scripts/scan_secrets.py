"""Secret and privacy scanner script for CI and local verification (DEV-006, SEC-007)."""

import re
import sys
from pathlib import Path

# SEC-007: Forbidden secret and token patterns
SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "OpenAI/Provider Secret Key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"bearer\s+[a-zA-Z0-9\-._~+/]{25,}=*", re.IGNORECASE), "Raw Bearer Token"),
    (re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----"), "Private Key Header"),
]

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
}

IGNORED_FILES = {
    ".env.example",
    "test_redaction.py",  # Contains synthetic secret test patterns
}

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".txt",
    ".sh",
    ".sql",
}


def scan_file(file_path: Path) -> list[str]:
    violations: list[str] = []
    if file_path.name in IGNORED_FILES:
        return violations

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        violations.append(f"Failed to read file {file_path}: {exc}")
        return violations

    for pattern, desc in SECRET_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            violations.append(f"Found {desc} in {file_path}: {len(matches)} occurrence(s)")

    return violations


def scan_repository(repo_root: Path) -> int:
    print(f"Scanning repository for leaked secrets and private tokens at {repo_root}...")
    all_violations: list[str] = []
    scanned_count = 0

    for path in repo_root.rglob("*"):
        if path.is_file():
            # Skip ignored directories
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if path.suffix in TEXT_EXTENSIONS or path.name in ("Dockerfile", "alembic.ini"):
                scanned_count += 1
                violations = scan_file(path)
                all_violations.extend(violations)

    print(f"Scanned {scanned_count} files.")
    if all_violations:
        print("\nERROR: Secret scan failed with the following findings:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("ALL SECRET SCANS PASSED! 0 critical findings.")
    return 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    sys.exit(scan_repository(root))
