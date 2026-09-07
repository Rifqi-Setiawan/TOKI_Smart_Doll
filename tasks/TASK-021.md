# TASK-021 â€” Freeze evaluation datasets, replay, and scorecards

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E5 â€” Evidence
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-018, TASK-020
- **Requirement IDs:** EVAL-001â€“006, REL-009
- **Architecture/ADR:** Reproducible evaluation architecture; ADR-015, ADR-016
- **Recommended agent capabilities:** `evaluation`, `AI_ML`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Create frozen versioned evaluation registries, deterministic replay/scorers, configuration baselines, human-review rubric, and release manifest schema.

## Context

Optional AI and competition claims may advance only from reproducible evidence against the release-under-test through the same contracts as runtime.

## Scope

- Dataset registry/schema/leakage checks for ASR, intent/answer, curriculum transitions, safety, reliability, and CV placeholder.
- Replay expected state/assessment/plan/fallback from audio/events.
- Hand-computable metric fixtures and automated sliced scorecards.
- Configurations: deterministic text/cache, speech hybrid, bounded-AI candidate.
- Human review rubric/disagreement/adjudication and release manifest fields.

## Out of Scope

- Collecting unsafe/unconsented data, implementing optional AI/CV, final soak/rehearsal.

## Relevant Architecture

- Exact release/config/dataset versions; deterministic checks before human/LLM judgment; optional features compared by ablation.

## Inputs

- Stable vertical slices, governed datasets, reviewer availability, requirement thresholds.

## Expected Outputs

- Evaluation package/datasets/configs/reports, scorers/tests, review forms, release manifest generator/schema.

## Implementation Requirements

- Split by child/speaker/session; freeze and checksum datasets; report coverage/limitations/slices.
- Scorers tested on hand-computable fixtures.
- Manifest pins code/image/DB/firmware/curriculum/policies/providers/prompts/thresholds/flags/results.

## Files / Modules Likely Involved

- `app/evaluation/`, `evaluation/datasets/`, `evaluation/configs/`, `evaluation/reports/`, scorer/regression tests.

## Constraints

- No aggregate-only claim. No test-set tuning. Raw media only in governed location/retention.

## Edge Cases

- Missing label, duplicate/leakage, provider nondeterminism, unsupported old fixture, reviewer disagreement.

## Error Cases

- Invalid/incomplete dataset or manifest blocks scorecard/release; never silently drop cases.

## Tests

- Dataset schema/uniqueness/leakage; replay determinism; scorer formulas; manifest completeness/reproducibility; config isolation.

## Evaluation

- ASR/understanding/response/E2E/reliability/human metrics exactly as requirements; sliced reports and confidence limitations.

## Acceptance Criteria

- [ ] Frozen versioned registries exist for every required category, with limitations explicit.
- [ ] Replay exercises the release through production contracts.
- [ ] Every metric passes hand-computable unit fixtures.
- [ ] Deterministic and speech baselines produce reproducible sliced scorecards.
- [ ] Human-review rubric/adjudication and complete release manifest schema exist.

## Risks

- Dataset scope becomes research-scale; freeze the minimum high-risk representative suite and add only evidence-driven cases.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting integrated speech/guardian baseline.
- Remaining work: Entire scope.
- Exact next action: Define dataset registry and hand-computable scorer fixtures before importing data.

## Definition of Done

DONE requires reproducible registries/replay/scorecards/manifest tests, review process, satisfied criteria, and no blocker.