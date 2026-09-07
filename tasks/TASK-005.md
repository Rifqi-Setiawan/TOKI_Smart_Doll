# TASK-005 — Add provider interfaces, fakes, and simulators

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E1 — Foundation
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-003
- **Requirement IDs:** AI-001–003, AI-006, DEV-004
- **Architecture/ADR:** Replaceable bounded adapters; ADR-004, ADR-008
- **Recommended agent capabilities:** `backend`, `AI_ML`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Provide vendor-neutral interfaces, deterministic fakes, and device/Flutter simulators so core development and tests never wait for external services or teams.

## Context

ASR, TTS, semantics, paraphrasing, and CV are replaceable evidence/rendering providers. Simulators exercise the same public contracts as real consumers.

## Scope

- Interfaces for ASR, TTS, semantic resolver, paraphraser, and CV.
- Deterministic success/abstain/timeout/malformed/error fakes.
- Minimal device handshake/turn simulator and Flutter progress consumer simulator.
- Adapter registry plus feature flags/budgets with providers disabled by default.

## Out of Scope

- Real provider SDKs, production UI, model selection, state-policy logic.

## Relevant Architecture

- SDK objects/errors cannot escape adapters; AI cannot access DB, tools, web, or device commands.

## Inputs

- TASK-003 contracts and cross-team fixtures.

## Expected Outputs

- Interface modules, deterministic fakes, simulators, configuration, contract tests, usage docs.

## Implementation Requirements

- Every call has deadline/budget hooks and normalized metadata/error.
- Fakes must be seed/config deterministic and support failure injection.
- Simulators use external API/WebSocket boundaries, not internal shortcuts.

## Files / Modules Likely Involved

- `app/speech/interfaces.py`, `app/understanding/interfaces.py`, `app/response/interfaces.py`, `app/vision/interfaces.py`, `app/providers/`, `simulators/`, `tests/provider_contract/`.

## Constraints

- No provider package unless needed for an interface-neutral contract. No runtime agent/tool loop.

## Edge Cases

- Cancellation, deadline expiry, stale result, unknown enum, deterministic repeated runs.

## Error Cases

- All fake/provider failures return or raise normalized typed outcomes and cannot mutate state.

## Tests

- Interface conformance for each fake; deterministic replay; failure modes; feature bypass; architectural dependency test preventing adapter-to-repository mutation.

## Evaluation

Not applicable — fakes/simulators; contract fidelity and determinism are the evaluation.

## Acceptance Criteria

- [ ] Every optional/provider dependency is replaceable by a deterministic fake.
- [ ] Device simulator completes versioned handshake and receives ACK/command fixtures.
- [ ] Flutter simulator validates progress DTO fixtures.
- [ ] Failure modes are reproducible and side-effect free.
- [ ] Architecture test proves providers cannot mutate authoritative state.

## Risks

- Unrealistic fakes hide integration bugs; base them on frozen external fixtures and add consumer contract tests later.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting contracts.
- Remaining work: Entire scope.
- Exact next action: Define adapter protocols from contracts, then implement deterministic failure matrix.

## Definition of Done

DONE requires interface/architecture tests, runnable simulators, docs, satisfied criteria, and no blocker.
