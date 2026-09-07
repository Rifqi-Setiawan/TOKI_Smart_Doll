# TASK-016 â€” Benchmark and integrate ASR adapter

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E3 â€” Speech Baseline
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-005, TASK-015
- **Requirement IDs:** AI-004, AI-005, AI-006, DATA-006, EVAL-002
- **Architecture/ADR:** Benchmark-selected ASR adapter; ADR-004, ADR-008
- **Recommended agent capabilities:** `AI_ML`, `backend`, `evaluation`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Compare at least two viable ASR candidates when feasible, select a primary through device-like Indonesian evidence, and integrate it behind normalized `ASRResult` with deadline/abstention.

## Context

Young-child Indonesian speech is the largest uncertainty. Provider reputation is not evidence; concept accuracy and calibrated abstention matter more than confident guesses.

## Scope

- Versioned audio dataset registry using consented device recordings or clearly labeled adult simulation until approval.
- Candidate adapters/benchmark runner and scorecard.
- Primary adapter integration with transcript hypothesis, timing/version/confidence evidence, abstain/error reason.
- Deadline, cancellation, size budget, and provider-error normalization.

## Out of Scope

- Fine-tuning, semantic LLM correction, production raw-audio retention, unrestricted transcript logs.

## Relevant Architecture

- AI output is evidence only; deterministic assessor decides; timeout/invalid result becomes `ABSTAIN`.

## Inputs

- Bounded audio service, provider credentials/quotas, data-processing approval, device-like labeled audio.

## Expected Outputs

- Adapter(s), benchmark/replay runner, dataset metadata, scorecard, selection/limitation decision entry, contract/failure tests.

## Implementation Requirements

- Split by speaker/session when identities exist; report noise/distance/speaker slices.
- Pin provider/model/version; do not convert provider confidence into correctness.
- If two-candidate comparison is impossible, document exact limitation and still establish reproducible baseline.

## Files / Modules Likely Involved

- `app/speech/asr/`, `app/evaluation/asr_replay.py`, `evaluation/datasets/asr/`, reports/tests.

## Constraints

- Privacy/consent governs fixtures. No live-child training/export. Provider can be disabled.

## Edge Cases

- Silence, clipped/high-pitched/noisy speech, code switching, empty/partial response, provider schema drift, quota/rate limit.

## Error Cases

- Timeout/malformed/provider failure â†’ normalized `ABSTAIN/ERROR`, safe retry/fallback, no false incorrectness.

## Tests

- Provider contract with frozen fixtures; timeout/cancel/malformed/rate-limit/schema drift; privacy scan; deterministic scorer fixtures.

## Evaluation

- WER, CER, expected-concept accuracy/recall, selective accuracy vs coverage, abstention, p50/p95, cost; slice by condition.

## Acceptance Criteria

- [ ] Reproducible scorecard compares â‰¥2 candidates or explicitly documents why not.
- [ ] Primary selection is evidence-backed and version-pinned.
- [ ] All outputs validate before assessment and failures abstain safely.
- [ ] Metrics include slices and do not rely on aggregate accuracy alone.
- [ ] Raw audio/transcripts comply with approved retention and normal logging rules.

## Risks

- Adult simulation overstates performance; label limitations and replace with governed device/child data when approved.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting audio path/data/provider access.
- Remaining work: Entire scope.
- Exact next action: Freeze dataset manifest and scorer fixtures before comparing providers.

## Definition of Done

DONE requires reproducible benchmark/selection, adapter/failure/privacy tests, satisfied criteria, and no blocker.