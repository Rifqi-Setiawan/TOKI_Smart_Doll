# TASK-024 â€” Evaluate constrained response paraphraser

## Metadata

- **Status:** TODO
- **Priority:** P1
- **Epic:** E6 â€” Optional AI
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-021, TASK-022; approved response constraints and reviewer availability
- **Requirement IDs:** FR-019, AI-008, EVAL-005
- **Architecture/ADR:** Optional surface realization only; ADR-007, ADR-016
- **Recommended agent capabilities:** `AI_ML`, `security`, `evaluation`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Generate optional natural wording from an already approved `ResponsePlan`, then promote or reject it through schema, provenance, developmental, safety, latency, and value evidence.

## Context

The deterministic template is always ready. The model cannot choose pedagogy/content/actions and receives no tools, web, memory, DB, or raw child media.

## Scope

- Independently flaggable low-temperature one-call paraphraser.
- Constraints: Indonesian, â‰¤25 spoken words, one concept, â‰¤1 question, allowed pedagogical act/grounding.
- Deterministic validators and template fallback.
- Frozen ablation and qualified human review.

## Out of Scope

- Unrestricted chatbot, curriculum generation, safety decision, dynamic activity planning.

## Relevant Architecture

- Candidate wording only; deterministic validation precedes TTS; no same-input repair/retry on critical path.

## Inputs

- Approved plans/templates, prompt/model candidate, frozen response/safety cases, reviewer rubric.

## Expected Outputs

- Paraphraser/flag/validators, AI contract/security tests, ablation/reviewer report, accept/reject decision.

## Implementation Requirements

- Template selected before call and remains fallback.
- Reject unknown grounding/action, blocked claim/topic, excess length/questions, malformed/unsafe/stale output.
- Pin prompt/model/version and call budget.

## Files / Modules Likely Involved

- `app/response/paraphraser.py`, `validators.py`, feature flags/budgets, AI tests, ablation reports.

## Constraints

- Remains off until gate passes; zero high-severity regression; total p95 â‰¤3 s.

## Edge Cases

- Prompt injection embedded in transcript, negation changing meaning, added clinical claim, second question, mixed language, stale plan.

## Error Cases

- Reject candidate and immediately use original template; no repeated model retry.

## Tests

- Constraint/property tests; malicious/malformed/timeout/stale; protected dependency direction; flag bypass; budget; template fallback.

## Evaluation

- 100% hard schema/provenance/language/length/safety, expert age-fit/recast rubric, latency/cost, value vs template, overblocking.

## Acceptance Criteria

- [ ] Model receives only bounded plan/context and has no tool/data access.
- [ ] All accepted outputs pass every hard validator; all rejected outputs fall back correctly.
- [ ] Zero high-severity safety regression and total p95 â‰¤3 s.
- [ ] Human review shows measurable value over templates on the named metric.
- [ ] Failed gate leaves feature disabled with documented decision.

## Risks

- Naturalness is hard to justify; require predefined metric/reviewer rubric and never delay reliability work.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Optional evidence-gated task created. |

## Handoff Notes

- Current state: Not ready until baseline/safety suites exist.
- Remaining work: Entire scope.
- Exact next action: Freeze the human-review rubric and hard validator fixture set.

## Definition of Done

DONE requires evidence-backed promotion or explicit rejection, all validator/fallback tests, documentation, and no blocker.