# TASK-008 — Implement protocol sequencing and resume core

## Metadata

- **Status:** DONE
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Antigravity (commit b3ea649)
- **Dependencies:** TASK-003, TASK-004, TASK-007
- **Requirement IDs:** FR-004, FR-005, DATA-002, DATA-004, API-006, SEC-004
- **Architecture/ADR:** Versioned device protocol; durable acknowledged state; ADR-003, ADR-012
- **Recommended agent capabilities:** `backend`, `debugging`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Implement transport-neutral validation for sequence, acknowledgement, idempotency, stale-result rejection, and resume using the device simulator.

## Context

Network delivery may duplicate, reorder, delay, or lose messages. These conditions must not repeat playback, attempts, or mastery updates.

## Scope

- Validate version/message/session/turn/sequence/timestamp fields.
- Deduplicate messages and reject stale/out-of-order callbacks with observable reason codes.
- Track last durable sent/acknowledged state and compute resume response.
- Define one bounded resend rule and session expiry behavior.

## Out of Scope

- Real WebSocket/device authentication, binary audio buffering, hardware commands.

## Relevant Architecture

- Optimistic `state_version`; only orchestrator applies accepted event; reconnect uses durable ACK state.

## Inputs

- Device contracts, DB constraints, FSM, simulator fixtures.

## Expected Outputs

- Sequencing/idempotency/resume service, repository operations, protocol reason codes, simulator integration tests.

## Implementation Requirements

- Checks occur before expensive/provider work.
- Idempotency key covers message/turn side effects.
- Replayed ACK/event returns stable outcome without repeating side effect.

## Files / Modules Likely Involved

- `app/device_protocol/sequencing.py`, `recovery.py`, repositories, simulator, protocol tests.

## Constraints

- No in-memory-only authoritative cursor; no unbounded resend.

## Edge Cases

- Sequence gap, duplicate with different payload, ACK after reconnect, expired session, callback for prior state version.

## Error Cases

- Conflict/replay/stale input yields typed rejection or idempotent prior result and trace; never partial mutation.

## Tests

- Duplicate, reorder, stale, gap, resend, reconnect/restart, concurrent version, and session-expiry integration tests.

## Evaluation

- Zero duplicate side effects and 100% expected resume outcome across a deterministic fault matrix.

## Acceptance Criteria

- [x] Duplicate/reordered/stale messages cannot advance state twice.
- [x] Resume starts from last durable acknowledged state after process restart.
- [x] One bounded resend is represented durably.
- [x] Conflict/replay outcomes are typed and observable.
- [x] Fault-matrix integration tests pass.

## Risks

- Firmware semantics may drift; isolate transport-neutral policy and freeze fixtures for TASK-019.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |
| 2026-09-07 | Antigravity | b3ea649 | Implemented ProtocolCursor model & Alembic migration 002, ProtocolRepository, ProtocolSequencer, ProtocolRecoveryManager, DeviceSimulator ACK helpers, documentation docs/device-protocol.md, and unit & fault matrix test suites (81/81 passed). |

## Handoff Notes

- Current state: Complete and verified.
- Remaining work: None for TASK-008.
- Exact next action: Proceed to TASK-009 ("Implement approved curriculum access") or TASK-006 ("Enforce CI and repository quality gates").

## Definition of Done

DONE requires restart/fault tests, protocol docs, satisfied criteria, and no blocker.

