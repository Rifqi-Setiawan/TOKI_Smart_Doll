# TASK-007 — Implement deterministic session state machine

## Metadata

- **Status:** DONE
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Antigravity
- **Dependencies:** TASK-003, TASK-004, TASK-005
- **Requirement IDs:** FR-001, FR-002, FR-010, FR-022, REL-001
- **Architecture/ADR:** Session orchestrator/FSM; ADR-003
- **Recommended agent capabilities:** `backend`, `testing`, `architecture_review`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Implement the explicit finite-state session control plane for one approved activity, including legal events, guards, deadlines, bounded retry, interrupt, and terminal behavior.

## Context

TOKI has no runtime agents. Only the orchestrator may advance authoritative state; providers supply evidence and callbacks with expected version.

## Scope

- State/event vocabulary and transition table for normal path plus silence, uncertainty, timeout, high-severity safety, stop, and cancellation.
- Pure transition decision function plus orchestrator persistence boundary.
- Retry count and deadline metadata; one child-friendly retry before activity-defined fallback.
- Stop/safety interrupt from every active state.

## Out of Scope

- Answer rules, response content, real speech/providers, device transport, mastery algorithm.

## Relevant Architecture

- One active turn per session; every state bounded; stale evidence ignored; safety overrides curriculum.

## Inputs

- TASK-003 contracts, TASK-004 state/version model, TASK-005 fakes, approved transition vocabulary.

## Expected Outputs

- State machine, orchestrator skeleton, policies/guards, transition matrix docs, exhaustive tests.

## Implementation Requirements

- Decision logic is deterministic and side-effect free; persistence occurs through explicit unit-of-work call.
- Illegal events produce typed rejection and audit outcome, not silent coercion.
- Provider callbacks cannot call repositories.

## Files / Modules Likely Involved

- `app/sessions/states.py`, `state_machine.py`, `orchestrator.py`, `policies.py`, `tests/unit/sessions/`.

## Constraints

- Only one activity and named exception paths. No dynamic workflow/agent framework.

## Edge Cases

- Stop during any state; duplicate/stale callback; deadline racing success; retry exhausted; terminal-session event.

## Error Cases

- Illegal/stale event cannot advance state. Internal error moves to a defined safe ending/recovery state without fabricated child outcome.

## Tests

- Table-driven every state/event pair; property tests for bounded exit, monotonic version, one active turn, no stale transition; safety/stop interrupt tests.

## Evaluation

- 100% defined transition coverage for implemented activity; no AI evaluation.

## Acceptance Criteria

- [x] Normal and named exception transitions are explicit and tested.
- [x] Only orchestrator has authoritative state mutation path.
- [x] Every active state has deadline/fallback/stop exit.
- [x] Retry is bounded to activity policy.
- [x] Property tests find no illegal terminal hang or stale transition.

## Risks

- Overgeneralizing future workflows; keep the transition set tied to one vertical slice.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |
| 2026-09-07 | Antigravity | b3ea649 | Implemented deterministic session state machine, SessionOrchestrator persistence boundary, table-driven tests, and property reachability/bounded retry tests. All 75 tests pass. |

## Handoff Notes

- Current state: Explicit session FSM, SessionOrchestrator persistence boundary, property & table-driven tests, and transition matrix documentation completed and verified (75 tests passing, ruff & mypy clean).
- Remaining work: None for TASK-007. Ready for protocol sequencing (TASK-008) and curriculum access (TASK-009).
- Exact next action: Proceed to TASK-008 ("Implement protocol sequencing and resume core") or parallel task (TASK-009 / TASK-006).

## Definition of Done

DONE requires transition/property tests, reviewed dependency direction, satisfied criteria, and no blocker.
