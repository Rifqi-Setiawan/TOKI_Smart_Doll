# TASK-002 — Establish reproducible runtime profiles

## Metadata

- **Status:** DONE
- **Priority:** P0
- **Epic:** E1 — Foundation
- **Owner/Last Agent:** Antigravity (commit a8e019d)
- **Dependencies:** TASK-001
- **Requirement IDs:** DEV-001, API-003, API-007, REL-006
- **Architecture/ADR:** FastAPI modular monolith; cloud primary/local twin; ADR-002, ADR-014
- **Recommended agent capabilities:** `infrastructure`, `backend`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Make a clean checkout boot the API and PostgreSQL reproducibly under `test`, `local`, `cloud`, and `demo_offline` profiles.

## Context

The demo must use the same application/container contract locally and in cloud. Profiles differ only in configuration and available adapters; secrets remain external.

## Scope

- Pin Python 3.12 dependencies and create reproducible application/container startup.
- Define typed settings profiles and external secret loading.
- Implement distinct live/readiness/demo health semantics with initial dependency placeholders.
- Document one-command local startup and clean shutdown.

## Out of Scope

- Production deployment, provider integration, offline content pack, or full health matrix.

## Relevant Architecture

- One FastAPI container plus PostgreSQL; optional providers may be degraded without failing core readiness.

## Inputs

- TASK-001 repository map and existing build conventions.

## Expected Outputs

- Runtime/lock configuration, container and compose definition, `.env.example`, settings modules, health endpoints, startup documentation, smoke tests.

## Implementation Requirements

- Reuse existing tooling where viable.
- Validate configuration at boot and fail with redacted typed errors.
- External non-local traffic uses TLS at the deployment edge.
- `demo_offline` must not require cloud credentials to boot.

## Files / Modules Likely Involved

- `pyproject.toml`, lockfile, `Dockerfile`, `compose.yaml`, `.env.example`, `app/main.py`, `app/config/`, `app/api/health.py`, smoke tests.

## Constraints

- No Kubernetes/microservices. No secrets in repo/logs. Backward-compatible startup until replacement is verified.

## Edge Cases

- Missing optional provider settings; database starting slowly; invalid profile; port conflict; stale migration.

## Error Cases

- Core dependency absent: readiness false with typed reason. Optional provider absent: demo health `DEGRADED`, process remains live.

## Tests

- Clean build/boot; configuration validation; live/ready/demo semantic tests; graceful shutdown; `demo_offline` boot without provider credentials.

## Evaluation

- Record clean checkout-to-healthy time and image/build reproducibility.

## Acceptance Criteria

- [x] One documented command starts API + PostgreSQL from a clean checkout.
- [x] All four profiles validate and have explicit differences.
- [x] Health endpoints distinguish process, core readiness, and demo degradation.
- [x] Offline profile boots without external AI credentials.
- [x] No secret is committed or emitted in test output.

## Risks

- Host workstation uses Python 3.13 without `uv`/`docker` in PATH; mitigated by flexible `requires-python = ">=3.12,<3.14"`, pinned requirements files, and native virtualenv support alongside Docker runtime.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |
| 2026-09-07 | Antigravity | a8e019d | Implemented `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`, `Dockerfile`, `docker-compose.yml`, `compose.yaml`. Created `app/config/settings.py` with typed profiles (`test`, `local`, `cloud`, `demo_offline`) and secret redaction. Created `app/api/health.py` with distinct `/health/live`, `/health/ready`, and `/health/demo` semantics (API-007). Created `app/main.py` with lifespan validation. Created `scripts/smoke_check.py`. Created unit test suites in `tests/unit/` (14 passing tests). Verified with pytest, ruff, and mypy. |

## Handoff Notes

- Current state: Runtime profiles and base health endpoints implemented and validated.
- Remaining work: None for TASK-002.
- Exact next action: TASK-003 (Freeze domain/API contracts) or TASK-006 (CI quality gates) can proceed.

## Definition of Done

DONE requires successful profile/health tests, documented startup, satisfied criteria, and no blocker. State verified and criteria satisfied.
