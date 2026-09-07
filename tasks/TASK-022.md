# TASK-022 â€” Enforce safety and failure regression gates

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E5 â€” Evidence
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-019, TASK-021
- **Requirement IDs:** SEC-005â€“010, REL-001â€“005, EVAL-002, EVAL-004
- **Architecture/ADR:** Safety fail-closed and evidence gate; ADR-001, ADR-015
- **Recommended agent capabilities:** `security`, `evaluation`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Freeze and enforce the â‰¥300-case Indonesian child-safety suite plus dependency failure matrix as mandatory CI/release gates.

## Context

Safety cannot rely on generic moderation or ad hoc demonstration. Required high-severity cases use reviewed immutable responses; every failure must reach a bounded safe state.

## Scope

- Cases for PII, sexual/adult, violence/danger, medical/diagnostic, manipulation/secrecy, prompt injection, abuse disclosure, distress, stop/help, Indonesian slang, ASR corruption, and overblocking controls.
- Failure injection for ASR, semantic/LLM placeholder, TTS, DB, network, CV placeholder, device ACK, malformed/stale callback.
- Deterministic expected action/response/provenance and qualified dual review/adjudication.
- CI thresholds and report.

## Out of Scope

- New generative capability, clinical diagnosis, final 30-minute soak.

## Relevant Architecture

- High-severity interrupt; canned reviewed content; uncertain/provider failure never becomes child error; core completes without LLM/CV.

## Inputs

- Safety catalog/policy, replay harness, device path, expert reviewers.

## Expected Outputs

- `child-safety-300-v1`, failure matrix, reviewer artifacts, automated gates/reports.

## Implementation Requirements

- Zero high-severity unsafe output; 100% required escalation action/provenance.
- Report overblocking and disagreements; do not hide excluded cases.
- CI blocks regressions and pins suite version.

## Files / Modules Likely Involved

- `evaluation/datasets/safety/`, `tests/failure_injection/`, `tests/regression/`, reports/CI config.

## Constraints

- No LLM-only judge. No unsafe raw personal data in cases. Immutable reviewed response IDs.

## Edge Cases

- Mixed benign/unsafe request, obfuscated slang, repeated distress, ASR deletion/substitution, safety+stop race, provider outage during escalation.

## Error Cases

- Any critical miss blocks promotion/release. Evaluator failure blocks the gate rather than assuming pass.

## Tests

- Dataset/scorer checks; all safety cases; failure matrix; canned-content integrity; safety interrupt; overblocking controls; CI gate behavior.

## Evaluation

- Critical violation count, escalation recall, safe redirect/refusal, overblocking, reviewer agreement, safe-terminal rate by failure.

## Acceptance Criteria

- [ ] â‰¥300 frozen cases cover named categories and ASR-corrupted variants.
- [ ] Zero high-severity unsafe outputs and 100% required canned escalations.
- [ ] No low-confidence/failure case is persisted as `INCORRECT`.
- [ ] Every named injected failure reaches a defined safe/recovery state.
- [ ] Dual review/disagreement/adjudication is recorded.
- [ ] Mandatory CI gate blocks a known failing fixture.

## Risks

- False confidence from narrow cases; publish slice coverage/limitations and preserve adversarial additions separately.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting replay and real-device baseline.
- Remaining work: Entire scope.
- Exact next action: Freeze category taxonomy, expected actions, and reviewer rubric before filling cases.

## Definition of Done

DONE requires frozen suite/failure gates, reviewer evidence, green CI, satisfied criteria, and no blocker.