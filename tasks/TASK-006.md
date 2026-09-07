# TASK-006 — Enforce CI and repository quality gates

## Metadata

- **Status:** READY
- **Priority:** P0
- **Epic:** E1 — Foundation
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-001
- **Requirement IDs:** DEV-002, DEV-005, DEV-006
- **Architecture/ADR:** Evidence/reliability as ongoing gates; ADR-015
- **Recommended agent capabilities:** `infrastructure`, `testing`, `documentation`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Make repository health and requirement traceability mandatory on every merge, with checks expanding as capabilities land.

## Context

AI agents must not hand off plausible but unvalidated code. CI is the shared, conversation-independent validation contract.

## Scope

- Add formatting/lint, type, unit, contract, migration, secret scan, and smoke-build jobs using existing tooling.
- Establish test markers/stages so fast checks run first and unavailable external services are not required.
- Add PR/commit evidence template: task, requirement IDs, test commands/results, rollback.
- Document how later safety/regression gates become required.

## Out of Scope

- Writing feature tests belonging to later tasks; deployment automation.

## Relevant Architecture

- Main remains runnable; one change/behavior per PR; no secrets; evidence is a release gate.

## Inputs

- TASK-001 baseline/tooling and current CI platform.

## Expected Outputs

- CI workflows, quality configuration, PR template/checklist, local equivalent command, flake policy.

## Implementation Requirements

- Reproduce checks locally; cache safely; pin action/tool versions.
- Fail on new secrets/type/contract/migration failures.
- Quarantine only documented pre-existing flaky tests with owner/expiry.

## Files / Modules Likely Involved

- `.github/workflows/` or equivalent, `pyproject.toml`, pre-commit config, `tests/`, PR template, `docs/testing.md`.

## Constraints

- Do not weaken tests to make CI green. Do not require live provider credentials for standard CI.

## Edge Cases

- Existing failures, slow migrations, forked PR without secrets, platform outage, generated schemas changing.

## Error Cases

- A failed required gate blocks REVIEW/DONE; the task/handoff records whether failure is pre-existing or introduced.

## Tests

- Validate workflow syntax; run local equivalent; intentionally verify representative lint/type/secret/schema failures in a safe fixture/branch.

## Evaluation

- Track CI duration, flake rate, and clean-checkout reproducibility.

## Acceptance Criteria

- [ ] Required checks run on change/PR and have a documented local equivalent.
- [ ] Standard CI uses deterministic fakes, not live provider credentials.
- [ ] Secret scan and migration/contract checks are mandatory when corresponding files exist.
- [ ] PR template requires task/requirements/tests/rollback.
- [ ] Baseline duration and any quarantined flake are recorded.

## Risks

- Slow CI encourages bypass; split fast/extended jobs and optimize measured bottlenecks.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting repository inventory.
- Remaining work: Entire scope.
- Exact next action: Identify current CI/toolchain and add the smallest mandatory fast gate.

## Definition of Done

DONE requires green CI validation, local reproduction docs, satisfied criteria, and no blocker.
