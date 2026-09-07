# TASK-002 — Establish reproducible runtime profiles

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E1 — Foundation
- **Owner/Last Agent:** Unassigned
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

- [ ] One documented command starts API + PostgreSQL from a clean checkout.
- [ ] All four profiles validate and have explicit differences.
- [ ] Health endpoints distinguish process, core readiness, and demo degradation.
- [ ] Offline profile boots without external AI credentials.
- [ ] No secret is committed or emitted in test output.

## Risks

- Environment drift; mitigate with pinned lockfile, same image, and CI smoke build.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting TASK-001.
- Remaining work: Entire scope.
- Exact next action: Map existing runtime conventions, then add the smallest compatible profiles.

## Definition of Done

DONE requires successful profile/health tests, documented startup, satisfied criteria, and no blocker.
