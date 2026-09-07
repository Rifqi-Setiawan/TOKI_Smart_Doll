# TASK-004 — Create PostgreSQL schema and migrations

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E1 — Foundation
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-002, TASK-003
- **Requirement IDs:** DATA-001–005, DATA-007–010, DEV-003
- **Architecture/ADR:** Authoritative PostgreSQL; atomic event/outbox; ADR-012, ADR-013
- **Recommended agent capabilities:** `backend`, `database`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Create the minimal authoritative persistence model and reversible migrations for devices/consent, curriculum, sessions, attempts, mastery, events, outbox, and version metadata.

## Context

In-process state is a cache. Durable state, optimistic concurrency, idempotency, append-only evidence, and privacy boundaries are prerequisites for safe orchestration and replay.

## Scope

- Async SQLAlchemy models/repositories and Alembic migrations.
- Unique/idempotency constraints, `state_version`, immutable curriculum versioning, append-only events, transactional outbox.
- Pseudonymous child/guardian linkage and consent/revocation representation.
- Seed only minimal test/demo records.

## Out of Scope

- Full repositories/business transactions, analytics projector, raw-media research storage, vector database.

## Relevant Architecture

- One PostgreSQL source of truth; no external broker/database; raw audio/frame absent from normal schema.

## Inputs

- TASK-003 contracts, data privacy decisions, existing schema/migrations.

## Expected Outputs

- Models, migrations, constraints/indexes, repository skeleton, seed fixtures, ER/data dictionary update.

## Implementation Requirements

- Backward-compatible migration strategy; immutable rows enforced where feasible.
- Event fields include IDs, sequence, type/time/schema/correlation/privacy class.
- Version metadata covers curriculum/model/prompt/policy/threshold/firmware/release.

## Files / Modules Likely Involved

- `app/persistence/models.py`, `repositories/`, `alembic/versions/`, `tests/migration/`, `docs/data-model.md`.

## Constraints

- No ChromaDB/second operational database. No exact DOB when age band suffices. No raw-media columns in normal entities.

## Edge Cases

- Concurrent session updates, duplicate message/turn, consent revocation, migration over existing rows, event ordering.

## Error Cases

- Constraint/concurrency failure rolls back cleanly and surfaces a normalized repository error.

## Tests

- Fresh upgrade, upgrade from existing baseline, rollback/data-plan verification, uniqueness/idempotency, optimistic concurrency, immutability, consent revocation persistence.

## Evaluation

Not applicable — deterministic data task; migration, integrity, and performance tests are sufficient.

## Acceptance Criteria

- [ ] Empty DB migrates to head and application boots.
- [ ] Stale `state_version` and duplicate IDs cannot partially mutate data.
- [ ] Approved curriculum versions and append-only events cannot be rewritten through normal repositories.
- [ ] Normal schema contains no retained raw media/direct child identifier.
- [ ] Migration and rollback/data plan tests pass.

## Risks

- Premature schema breadth; keep minimal columns and evolve additively.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting runtime and contracts.
- Remaining work: Entire scope.
- Exact next action: Compare existing DB head to the minimum entity/invariant list.

## Definition of Done

DONE requires migration/integrity tests, current data docs, satisfied criteria, and no blocker.
