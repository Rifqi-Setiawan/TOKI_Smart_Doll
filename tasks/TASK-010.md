# TASK-010 — Implement deterministic answer assessment

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-003, TASK-009
- **Requirement IDs:** FR-008, FR-009, FR-010, AI-005, OBS-005
- **Architecture/ADR:** Deterministic-first understanding; ADR-006
- **Recommended agent capabilities:** `backend`, `AI_ML`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Resolve expected activity answers through normalization, exact/synonym/phonetic/context rules while preserving `UNCERTAIN` and `NO_SPEECH` as system uncertainty, never child incorrectness.

## Context

Provider confidence is evidence, not truth. The baseline must be fast, interpretable, and strong enough to measure whether semantic AI adds value later.

## Scope

- Indonesian casing/punctuation/whitespace normalization.
- Exact, approved synonym, simple phonetic/common-variant, silence, unrelated, and confidence-policy paths.
- Typed `CORRECT`, `INCORRECT`, `UNCERTAIN`, `NO_SPEECH` with rule/provenance explanation.
- Frozen initial labeled fixtures.

## Out of Scope

- LLM semantic resolver, fine-tuned IndoBERT, free-form intent taxonomy, mastery mutation.

## Relevant Architecture

- Deterministic assessor precedes optional AI; only sufficient evidence can produce `INCORRECT`.

## Inputs

- Approved answer spec/synonyms, ASR evidence contract, uncertainty thresholds/policy version.

## Expected Outputs

- Normalizer, assessor, rule catalog, labeled fixtures, metrics/confusion report.

## Implementation Requirements

- Pure/reproducible decision from versioned inputs.
- Record matched rule and confidence/uncertainty reason.
- Keep thresholds/config versioned; no provider-specific confidence assumption.

## Files / Modules Likely Involved

- `app/understanding/normalization.py`, `deterministic_assessor.py`, rules/fixtures/tests.

## Constraints

- No forced guess. No live interaction auto-training. Changes require regression evidence.

## Edge Cases

- Empty/punctuation-only input, repeated words, multiple candidates, near-homophone, contradictory confidence, off-topic stop/help.

## Error Cases

- Malformed evidence becomes `UNCERTAIN`/typed error and cannot become `INCORRECT`.

## Tests

- Table-driven fixtures; property invariant for all low-confidence/error statuses; deterministic repeatability; stop/help precedence.

## Evaluation

- Macro-F1/confusion matrix, false-incorrect rate, abstention/coverage, sliced by rule and input condition.

## Acceptance Criteria

- [ ] Frozen fixtures reproduce expected assessment and explanation code.
- [ ] False-incorrect count for low-confidence/no-speech/malformed inputs is zero.
- [ ] Exact/common approved variants bypass model calls.
- [ ] Results include policy/rule/content provenance.
- [ ] Metric calculator output is recorded for the baseline fixture.

## Risks

- Rules can overfit; keep blinded additions for TASK-021 and report coverage.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting curriculum task.
- Remaining work: Entire scope.
- Exact next action: Freeze labeled examples and the uncertainty truth table before adding rules.

## Definition of Done

DONE requires invariant/fixture tests, baseline metrics, satisfied criteria, and no blocker.
