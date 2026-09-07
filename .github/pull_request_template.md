## Summary of Change

<!-- Provide a concise description of the bounded behavior or enabler implemented in this PR (DEV-002). -->

## Task Reference

- **Task ID:** TASK-XXX
- **Task Title:** <title>
- **Epic:** <E1-E8>

## Requirement IDs

<!-- List every functional, AI, security, data, or reliability requirement fulfilled by this PR -->
- [ ] Requirements: `REQ-XXX`, `...`

## Evidence & Validation Commands

<!-- Paste exact commands executed locally and their outcomes (must be reproducible) -->
- [ ] `python scripts/run_quality_gates.py` → PASS
- [ ] `pytest tests/<relevant_tests> -v` → PASS
- [ ] `ruff check app tests simulators alembic scripts` → PASS
- [ ] `mypy app simulators tests scripts` → PASS

## Secret & Privacy Verification

- [ ] `python scripts/scan_secrets.py` reports zero critical findings (SEC-007, DEV-006).
- [ ] Zero raw child media, passwords, API tokens, or direct PII stored or leaked.

## Rollback Plan

<!-- Describe exact rollback mechanism if regression is detected post-merge (DEV-002) -->
- **Rollback steps:** Revert PR commit / deploy previous release image / disable feature flag `<FLAG_NAME>`.
- **Database impact:** Backward-compatible migration (no data loss on rollback).
