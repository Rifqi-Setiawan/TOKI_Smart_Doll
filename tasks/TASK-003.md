# TASK-003 — Freeze versioned domain and API contracts

## Metadata

- **Status:** READY
- **Priority:** P0
- **Epic:** E1 — Foundation
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-001
- **Requirement IDs:** API-001, API-002, API-004, API-005, API-006, AI-002
- **Architecture/ADR:** Boundary contracts; AI evidence-only; ADR-003, ADR-004
- **Recommended agent capabilities:** `backend`, `architecture_review`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Freeze minimal versioned Pydantic v2/JSON Schema contracts and golden fixtures that let backend, hardware, Flutter, CV, and AI adapters develop independently.

## Context

Control remains deterministic only if every external/probabilistic boundary is typed and rejects malformed or stale data before policy code sees it.

## Scope

- Define `DeviceEnvelope`, commands/ACK, session events, `ASRResult`, assessment, `ResponsePlan`, TTS output, CV observation, learning evidence, and progress DTOs.
- Include `schema_version`, correlation IDs, provider/model/policy versions, latency/status, and abstain/error semantics where relevant.
- Export schemas and valid/invalid fixtures; document additive vs breaking change policy.

## Out of Scope

- Provider SDK code, database models, state transitions, UI implementation.

## Relevant Architecture

- Only orchestrator mutates state; binary audio is separate from compact JSON control envelopes; unknown enum values are rejected.

## Inputs

- Hardware codec/envelope draft, Flutter DTO needs, CV provisional schema, approved state/event vocabulary.

## Expected Outputs

- Contract modules, generated JSON Schemas, fixture catalog, contract compatibility tests, contract ownership notes.

## Implementation Requirements

- Use strict typed enums/unions and explicit optionality.
- Error responses must not expose stack, prompt, credential, or raw provider payload.
- Callback contracts include `session_id`, `turn_id`, expected `state_version`.

## Files / Modules Likely Involved

- `app/*/contracts.py`, `schemas/`, `tests/contract/`, `tests/fixtures/contracts/`, API documentation.

## Constraints

- Minimal v1 only; unresolved cross-team fields must be explicit. No breaking changes without version + ADR.

## Edge Cases

- Unknown enum/version, extra fields, clock skew, duplicate IDs, partial ASR, absent confidence, stale callbacks.

## Error Cases

- Invalid input returns a stable typed error before side effects; invalid AI contract maps to error/abstain, never guessed defaults.

## Tests

- Round-trip per contract; invalid/unknown version; enum rejection; JSON Schema snapshots; backward-compatible additive change; redacted error snapshots.

## Evaluation

- Count unresolved cross-team fields and consumer fixture compatibility; no model evaluation.

## Acceptance Criteria

- [ ] Every named boundary has a Pydantic contract and exported schema.
- [ ] Valid/invalid golden fixtures are consumable by hardware/Flutter/CV simulators.
- [ ] All probabilistic outputs carry status/version/latency and abstain/error semantics.
- [ ] Stale callback correlation fields are mandatory.
- [ ] Contract tests and redacted error snapshots pass.

## Risks

- Contract churn blocks teams; freeze minimal v1 and use additive evolution.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting repository inventory.
- Remaining work: Entire scope.
- Exact next action: Compare existing models to the required boundary list and create a gap table.

## Definition of Done

DONE requires schema/compatibility tests, consumer-review evidence, satisfied criteria, and no blocker.
