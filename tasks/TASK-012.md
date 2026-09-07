# TASK-012 — Persist attempts, mastery, events, and outbox atomically

## Metadata

- **Status:** DONE
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Antigravity (commit b3ea649)
- **Dependencies:** TASK-004, TASK-007, TASK-010, TASK-011
- **Requirement IDs:** FR-014, FR-015, DATA-004, DATA-005
- **Architecture/ADR:** Atomic resolved-turn transaction; ADR-011, ADR-012
- **Recommended agent capabilities:** `backend`, `database`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Commit an eligible resolved turn, attempt/evidence, optional transparent mastery update, session snapshot, domain event, and outbox record as one idempotent transaction.

## Context

Parent progress and replay are trustworthy only if state, evidence, mastery, and emitted events cannot diverge during crashes/retries.

## Scope

- Unit-of-work service for resolved turn.
- Neutral learning evidence and replaceable versioned rule-based mastery policy with explanation code.
- Idempotent outbox/event write and optimistic state update.
- Failure injection at each write boundary.

## Out of Scope

- Outbox consumer/projection, BKT, async broker, parent API.

## Relevant Architecture

- PostgreSQL transaction is authoritative; uncertain/no-speech evidence is ineligible for incorrect/mastery penalty.

## Inputs

- Session transition, assessment, response plan, DB repositories, provisional expert-approved mastery rule.

## Expected Outputs

- Unit of work, mastery interface/rule, event payload, transactional tests, reproducibility fixture.

## Implementation Requirements

- Idempotency by message/turn; duplicate returns prior durable outcome.
- Mastery result records previous/new value, policy version, evidence IDs, explanation.
- Any write failure rolls back all writes.

## Files / Modules Likely Involved

- `app/persistence/unit_of_work.py`, repositories/outbox, `app/mastery/rules.py`, integration tests.

## Constraints

- No AI-derived mastery, no separate broker transaction, no partial retry of non-idempotent work.

## Edge Cases

- Duplicate commit, concurrent state version, uncertainty, terminal session, outbox uniqueness conflict, mastery disabled.

## Error Cases

- Transaction error leaves prior state intact and yields typed retryability; retry only the whole idempotent transaction.

## Tests

- Rollback injected after every write; duplicate replay; concurrent stale update; mastery reproducibility; uncertainty ineligibility; event/outbox equality.

## Evaluation

- Reproduce mastery/output from prior state + evidence + policy version; zero partial rows across failure matrix.

## Acceptance Criteria

- [x] All six resolved-turn records commit atomically or none do.
- [x] Replay creates zero duplicate attempts/mastery/events/outbox.
- [x] Mastery is transparent/versioned/reproducible and skips uncertain evidence.
- [x] Stale state cannot commit partial data.
- [x] Failure-injection transaction tests pass.

## Risks

- Mastery ownership unclear; keep evidence neutral and rule interface replaceable.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |
| 2026-09-07 | Antigravity | b3ea649 | Implemented `ResolvedTurnUnitOfWork` with nested transactional rollback and 6 artificial failure injection boundaries. Implemented pure, transparent `RuleBasedMasteryPolicy` with uncertainty guard (FR-009, FR-015, ADR-011). Verified replay idempotency (`message_id`), optimistic locking (`state_version`), payload equality for outbox/event, and 0 partial writes across failure injection matrix (`tests/integration/test_unit_of_work.py`). 173/173 tests pass; mypy and ruff 100% clean. |

## Handoff Notes

- Current state: ResolvedTurnUnitOfWork and RuleBasedMasteryPolicy fully implemented and verified with failure injection and reproducibility tests.
- Remaining work: None for TASK-012.
- Exact next action: Proceed to TASK-013 (Build progress projection and turn observability).

## Definition of Done

DONE requires atomicity/idempotency/reproducibility tests, satisfied criteria, and no blocker.

