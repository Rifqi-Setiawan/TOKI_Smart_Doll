# TASK-014 — Prove deterministic end-to-end vertical slice

## Metadata

- **Status:** IN_PROGRESS
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Antigravity (commit b3ea649)
- **Dependencies:** TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012, TASK-013
- **Requirement IDs:** REL-005, DEV-002, EVAL-001
- **Architecture/ADR:** One text/cached-audio activity; ADR-003, ADR-015
- **Recommended agent capabilities:** `testing`, `backend`, `evaluation`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Wire and prove one complete deterministic activity: start → prompt → simulated text answer → assessment → response → atomic evidence → progress read, with no external AI.

## Context

This is the first functional demo and the stable fallback baseline for every later speech/AI feature.

## Scope

- API/device-simulator wiring of existing components.
- Normal, uncertain, no-speech/retry, safety-stop, duplicate, and restart scenarios.
- Local latency measurement and recorded demonstration fixture.
- Fix only integration defects required for this slice.

## Out of Scope

- Real audio/provider/device/Flutter, optional semantic AI, broad refactors.

## Relevant Architecture

- Deterministic control and cached template output; PostgreSQL durable evidence; provider fakes only.

## Inputs

- Completed TASK-005–013 artifacts and one approved activity.

## Expected Outputs

- End-to-end tests, runnable demo command/script, trace/evidence capture, baseline report.

## Implementation Requirements

- Exercise public API/protocol boundaries and real test PostgreSQL.
- Preserve repeatability through fixed fixtures/clock where needed.
- Record exact release/config/fixture versions.

## Files / Modules Likely Involved

- API wiring, `tests/e2e/test_text_activity.py`, `demo/fixtures/`, initial evaluation report.

## Constraints

- No live provider credentials. Orchestration+persistence p95 target <150 ms locally.

## Edge Cases

- Process restart between prompt/answer, duplicate answer, projector lag, uncertain then retry, stop at each state.

## Error Cases

- Every injected failure reaches a typed safe state and leaves consistent durable records.

## Tests

- Full happy/uncertain/no-speech/safety/duplicate/restart E2E matrix plus required CI suite.

## Evaluation

- Completion, transition coverage, duplicate effects, projection consistency, server p50/p95 excluding network/audio.

## Acceptance Criteria

- [ ] One command runs the full deterministic activity from a clean local environment.
- [ ] All named scenarios produce expected durable state/progress/trace.
- [ ] Duplicate/illegal events create zero duplicate effects.
- [ ] No uncertainty is recorded as incorrect.
- [ ] Local orchestration+persistence p95 is <150 ms or a measured blocker is explicitly accepted before continuation.
- [ ] CI is green and demonstration evidence is versioned.

## Risks

- Integration task can absorb unrelated fixes; create follow-up backlog items unless the defect blocks acceptance.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting deterministic foundation.
- Remaining work: Entire scope.
- Exact next action: Run the happy-path E2E first, then add one failure scenario at a time.

## Definition of Done

DONE requires reproducible E2E evidence, all scenario/latency gates, updated docs, and no blocker.
