# TASK-011 — Implement response planning and core safety

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-003, TASK-009, TASK-010
- **Requirement IDs:** FR-011, FR-012, FR-013, SEC-005, SEC-009
- **Architecture/ADR:** Template-first planner and deterministic safety; ADR-001, ADR-007, ADR-009
- **Recommended agent capabilities:** `backend`, `security`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Produce a validated, template-backed `ResponsePlan` for each assessment/safety outcome, including cached audio and safe stop/escalation fallbacks.

## Context

The planner—not an LLM—chooses pedagogical act, approved text/template, gesture, provenance, retry/fallback, and immutable high-severity response.

## Scope

- Plan correct/incorrect/uncertain/no-speech/retry/hint/choice/imitation/end outcomes for one activity.
- Detect initial high-severity/stop/help policy cases and interrupt active flow.
- Validate plan schema, approved provenance, allowed action, response length/content, and cache reference.
- Select reviewed canned escalation and safe end-session audio.

## Out of Scope

- Generative paraphrasing, exhaustive 300-case suite, dynamic TTS implementation, clinical advice.

## Relevant Architecture

- Deterministic plan always exists before optional variation; safety fail-closed; TTS only receives final approved text.

## Inputs

- Assessment, activity policy/templates, safety catalog, session state, cache manifest.

## Expected Outputs

- Planner, validators, initial safety policy/catalog, fallback matrix, tests.

## Implementation Requirements

- One retry maximum before activity-defined fallback.
- High severity overrides curriculum immediately.
- Every plan includes curriculum/template/policy provenance.
- Missing/invalid template never triggers generation; use reviewed generic fallback/stop.

## Files / Modules Likely Involved

- `app/response/planner.py`, `validators.py`, `app/safety/policy.py`, `catalog.py`, fixtures/tests.

## Constraints

- No diagnosis/emotion claim/free chat. Canned high-severity content immutable and reviewed.

## Edge Cases

- Missing audio, exhausted retry, simultaneous stop+safety, stale activity, invalid gesture, oversized response.

## Error Cases

- Invalid/missing plan fails closed to a valid reviewed fallback and records reason; never emit partial/unvalidated output.

## Tests

- Decision tables for all outcomes; safety interrupt from every active state; provenance/length/content validators; fallback on missing/corrupt template; stop without provider.

## Evaluation

- 100% schema/provenance on initial suite; qualified review of child appropriateness for pilot templates.

## Acceptance Criteria

- [ ] Every implemented outcome returns a valid approved `ResponsePlan`.
- [ ] Required high-severity cases select immutable canned response immediately.
- [ ] Retry/fallback is bounded and state-compatible.
- [ ] Stop/end works without ASR/LLM/TTS dynamic providers.
- [ ] Missing/invalid content uses reviewed fallback and is observable.

## Risks

- Safety policy may be incomplete; constrain this task to initial mandatory cases and expand/freeze in TASK-022.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting dependencies and reviewed catalog.
- Remaining work: Entire scope.
- Exact next action: Create the assessment×state response decision table and safety precedence fixtures.

## Definition of Done

DONE requires planner/safety/fallback tests, reviewer evidence, satisfied criteria, and no blocker.
