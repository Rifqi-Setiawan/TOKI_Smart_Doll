# TASK-013 — Build progress projection and turn observability

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-012
- **Requirement IDs:** FR-016, FR-017, FR-021, OBS-001–005
- **Architecture/ADR:** Event-derived read model and per-turn trace; ADR-012, ADR-015
- **Recommended agent capabilities:** `backend`, `data`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Project durable events into non-clinical progress/session summaries and expose one privacy-redacted trace per turn with provenance, state, outcomes, fallbacks, and latency.

## Context

Parent evidence and judge-facing observability must agree with durable attempts. Telemetry is asynchronous and must never delay audio response.

## Scope

- Idempotent outbox consumer/projector and rebuild command.
- Minimal progress/session DTO data source, without authentication wiring yet.
- Root turn trace and stage/outcome attributes; required metrics primitives.
- Redaction rules and telemetry-outage isolation.

## Out of Scope

- Flutter UI/auth, full dashboard, raw transcript/media export, final metric scorecards.

## Relevant Architecture

- Projection rebuilds from append-only events; uncertainty separated from child performance; trace does not expose PII/media.

## Inputs

- Transaction events/outbox, progress contracts, telemetry conventions, privacy policy.

## Expected Outputs

- Projector/rebuild, query service/API skeleton, traces/metrics, redaction tests, evidence view fixture.

## Implementation Requirements

- Consumer idempotent and eventually consistent; lag measured.
- Store anonymized IDs and version/provenance, not raw media/provider payload.
- Telemetry exporter failure cannot fail a turn.

## Files / Modules Likely Involved

- `app/analytics/projector.py`, `projections.py`, `app/api/progress.py`, `app/telemetry/`, tests.

## Constraints

- Non-clinical language only. No low-confidence case displayed as incorrect/mastery evidence.

## Edge Cases

- Duplicate/out-of-order outbox delivery, rebuild during live writes, projector crash, telemetry unavailable, missing optional mastery.

## Error Cases

- Projection lag/failure is observable and retryable; authoritative attempt remains unchanged. Telemetry errors are swallowed only after local redacted outcome record.

## Tests

- Idempotent projection; rebuild equivalence; duplicate/out-of-order event; telemetry failure; required trace attributes; redaction/privacy scan; uncertainty display invariant.

## Evaluation

- Projection consistency and lag; trace completeness; zero critical privacy findings.

## Acceptance Criteria

- [ ] Rebuild produces the same projection from the same event stream.
- [ ] One sample turn is traceable through state, provenance, outcome, fallback, latency, and mastery explanation.
- [ ] Telemetry outage does not fail/slow the core transaction materially.
- [ ] Uncertain/no-speech evidence is distinct from child incorrectness.
- [ ] Redaction scan reports zero critical findings.

## Risks

- Eventual consistency confuses demo; expose last-updated/pending status and measure lag.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting atomic event path.
- Remaining work: Entire scope.
- Exact next action: Define projection equations/DTO fields from versioned events, then write rebuild equivalence test.

## Definition of Done

DONE requires rebuild/trace/redaction tests, measured lag, satisfied criteria, and no blocker.
