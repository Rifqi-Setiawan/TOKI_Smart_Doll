# TASK-027 â€” Pass security, replay, soak, and parity gates

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E7 â€” Reliability
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-020, TASK-022, TASK-026
- **Requirement IDs:** REL-006, REL-009, REL-010, SEC-001â€“009
- **Architecture/ADR:** Release reliability/privacy gate; ADR-013, ADR-014, ADR-015
- **Recommended agent capabilities:** `testing`, `security`, `infrastructure`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Pass the complete pre-release operational gate: authorization/input/privacy security, 200-turn replay, 30-minute soak, restart/reconnect/outage recovery, and cloud-local parity.

## Context

This task validates the integrated release candidate; it should not introduce features. Defects are fixed narrowly or returned to the owning task.

## Scope

- Auth/resource/rate/size/replay/secret/redaction security tests and scan.
- 200-turn frozen replay with restart/duplicate/stale conditions.
- 30-minute soak with memory/connection/resource monitoring.
- Packet loss/internet loss/DB/provider/device reconnect and recovery.
- Exact cloud/local image/config/contract comparison and health evidence.

## Out of Scope

- Feature additions, architecture change, optional AI promotion, full penetration test/certification.

## Relevant Architecture

- Zero illegal transition/duplicate/state divergence; bounded resources; zero raw media/PII in normal outputs.

## Inputs

- Integrated release candidate, frozen suites, offline pack, target laptop/cloud profiles.

## Expected Outputs

- Security scan/report, 200-turn replay report, soak resource graphs, recovery/parity report, blocking defect list.

## Implementation Requirements

- Pin commit/image/config/datasets. Use venue-equivalent settings.
- Never weaken thresholds; link fixes to owning task/requirement.
- Sanitize reports/fixtures.

## Files / Modules Likely Involved

- `tests/security/`, `tests/soak/`, failure/replay configs, evaluation reports, deployment profiles.

## Constraints

- No manual DB edits to make runs pass. No hidden retries or discarded failures.

## Edge Cases

- Slow leak, half-open breaker during soak, token revocation, clock skew, buffer recovery, repeated reconnect.

## Error Cases

- Any critical security/privacy issue, replay divergence, unbounded growth, or unrecovered disconnect blocks TASK-028.

## Tests

- Named security matrix; 200-turn replay; 30-minute soak; recovery matrix; cloud/local same-image smoke; report reproducibility.

## Evaluation

- Critical findings, divergence/duplicates, recovery rate/time, p95/p99/resource slopes, privacy findings, parity mismatches.

## Acceptance Criteria

- [ ] Cross-guardian/replay/oversize/rate-limit/secret/redaction tests pass.
- [ ] 200 turns have zero illegal transition, duplicate attempt, or state divergence.
- [ ] 30-minute soak has no unrecovered disconnect or unbounded resource growth.
- [ ] Normal logs/traces/reports have zero raw media/direct identifier critical findings.
- [ ] Cloud and local use the same image/contracts and both pass core smoke.
- [ ] All critical defects are resolved and rerun on the same pinned candidate.

## Risks

- Late failures pressure threshold weakening; freeze gates in advance and cut optional features instead.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial release-gate task created. |

## Handoff Notes

- Current state: Awaiting integrated/offline release candidate.
- Remaining work: Entire scope.
- Exact next action: Pin candidate/manifest, then run security fast gate before long replay/soak.

## Definition of Done

DONE requires all pinned security/replay/soak/parity reports passing, satisfied criteria, and no blocker.