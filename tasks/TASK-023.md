# TASK-023 â€” Evaluate bounded semantic resolver

## Metadata

- **Status:** TODO
- **Priority:** P1
- **Epic:** E6 â€” Optional AI
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-021, TASK-022; representative ambiguous-turn set and approved prompt/model
- **Requirement IDs:** FR-018, AI-007, EVAL-005
- **Architecture/ADR:** Optional ambiguity-only semantic evidence; ADR-006, ADR-016
- **Recommended agent capabilities:** `AI_ML`, `evaluation`, `backend`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Implement an independently flaggable fixed-schema semantic resolver for unresolved eligible turns, then promote or reject it through frozen ablation.

## Context

The resolver is not required for the demo. It may interpret ambiguity but cannot choose activity, mutate state/mastery/safety, access tools/web/DB, or replace deterministic common paths.

## Scope

- Eligibility gate after deterministic assessment.
- Vendor-neutral adapter prompt/input budget and typed evidence/`ABSTAIN`.
- Deadline, one call/no same-input retry, validation, stale-result rejection, cost metrics.
- Enabled/disabled replay and documented promotion decision.

## Out of Scope

- Free chat, agent tools, response generation, fine-tuned IndoBERT, vector retrieval.

## Relevant Architecture

- AI candidate passes deterministic policy; invalid/slow/unsafe/uncertain output is discarded.

## Inputs

- Frozen ambiguous cases, deterministic baseline, model/provider candidate, approved schema/prompt.

## Expected Outputs

- Resolver/eligibility/flag/budget, contract/security tests, ablation report, accept/reject decision.

## Implementation Requirements

- Exact/common intents make zero calls.
- Fixed schema/provenance/version/latency; no arbitrary content/tool field.
- Immediate flag rollback without schema migration.

## Files / Modules Likely Involved

- `app/understanding/semantic_resolver.py`, provider adapter, flags/budgets, AI contract/regression tests, ablation report.

## Constraints

- Remains off until promotion. No safety/latency regression; p95 total â‰¤3 s.

## Edge Cases

- Prompt injection, off-curriculum phrase, ambiguous multi-intent, stale answer, malformed enum, timeout.

## Error Cases

- Any invalid/timeout/stale output maps to `ABSTAIN` and deterministic retry/fallback without provider retry.

## Tests

- Eligibility/no-call; schema/malformed/timeout/stale; injection/off-topic; cannot mutate protected layers; feature bypass/cost budget.

## Evaluation

- Ambiguous-turn completion lift, false-incorrect, selective accuracy/coverage, safety, schema/provenance, p95, cost; deterministic vs enabled ablation.

## Acceptance Criteria

- [ ] Exact/common paths make zero resolver calls.
- [ ] 100% valid accepted outputs have schema/provenance and protected dependency direction.
- [ ] Failure/abstain path preserves deterministic success.
- [ ] Promotion requires â‰¥5 percentage-point absolute ambiguous-turn completion lift, zero high-severity regression, and total p95 â‰¤3 s (or a documented statistically defensible recalibration).
- [ ] Feature remains disabled and decision records rejection if gate fails.

## Risks

- Sophistication without benefit; negative result is valid and must not delay TASK-026.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Optional evidence-gated task created. |

## Handoff Notes

- Current state: Not ready until baseline/safety suites exist.
- Remaining work: Entire scope.
- Exact next action: Verify dataset power/coverage and freeze promotion metric before implementation.

## Definition of Done

DONE requires either evidence-backed promotion or explicit rejection/removal, full regression tests, docs, and no blocker.