# TASK-001 — Inventory repository and map boundaries

## Metadata

- **Status:** DONE
- **Priority:** P0
- **Epic:** E1 — Foundation
- **Owner/Last Agent:** Antigravity (commit a8e019df526ffde379f9692cf585c480370c6065)
- **Dependencies:** None
- **Requirement IDs:** DEV-001, DEV-002
- **Architecture/ADR:** Modular monolith; ADR-002; source-of-truth hierarchy
- **Recommended agent capabilities:** `repository_inspection`, `architecture_review`, `documentation`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Produce an evidence-based map of the existing repository so later agents extend current conventions safely instead of assuming the roadmap's illustrative paths.

## Context

The approved roadmap was produced without access to the TOKI repository tree. Its module names are target boundaries, not permission for a rewrite. This task resolves that uncertainty before implementation begins.

## Scope

- Record language/runtime versions, entry points, package boundaries, configuration, tests, migrations, CI, containers, scripts, and current runnable paths.
- Map existing modules to approved responsibilities and list gaps/conflicts.
- Record branch, commit, worktree, known failing tests, and local start commands.
- Reconcile the single canonical architecture decision-log path as `docs/decisions.md` without maintaining duplicate histories.

## Out of Scope

- Production behavior changes, broad restructuring, dependency upgrades, or architecture redesign.

## Relevant Architecture

- Modular monolith with FastAPI, PostgreSQL, deterministic FSM, provider adapters, evaluation, and local demo profile.

## Inputs

- Repository tree and git history; `requirements.md`; target architecture; accepted decision log; implementation roadmap.

## Expected Outputs

- `docs/repository-map.md` with module/test/data/deployment ownership map.
- Updated task path notes where repository conventions differ.
- Recorded baseline commands/results and explicitly listed gaps.

## Implementation Requirements

- Inspect before changing files. Preserve unrelated user work.
- Distinguish confirmed state, discrepancy, assumption, and recommendation.
- Link each material gap to requirement/ADR/task IDs.

## Files / Modules Likely Involved

- `README.md`, `pyproject.toml`, application packages, tests, migrations, CI configuration, containers, `docs/repository-map.md`, `docs/decisions.md`.

## Constraints

- No cosmetic restructure. No destructive git action. No secret or sensitive-data output.

## Edge Cases

- Dirty worktree; multiple apps; missing migrations; generated/vendor directories; stale docs; no test runner.

## Error Cases

- If repository or required docs are unavailable, mark `BLOCKED` and record exact missing access; do not fabricate the inventory.

## Tests

- Run existing documented smoke/test commands without modifying state where practical; record command, environment, exit code, and pre-existing failures.

## Evaluation

Not applicable — documentation/inspection task; completeness and reproducibility checks are sufficient.

## Acceptance Criteria

- [x] Current branch, commit, worktree, runtime, entry points, tests, migrations, CI, and start path are recorded.
- [x] Existing modules are mapped to every roadmap responsibility or marked missing.
- [x] Baseline command results distinguish pre-existing failures.
- [x] No production code or architecture was silently changed.
- [x] `tasks/index.md` path assumptions are corrected when evidence requires it.

## Risks

- Missing a hidden path can cause duplicate modules; mitigated with `git ls-files`, inspection of filesystem directories, and verification of target conventions in `docs/repository-map.md`.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created from approved roadmap caveat. |
| 2026-09-07 | Antigravity | a8e019d | Inspected repository tree, git status/history, host runtime tools (Python 3.13.14, pip, missing uv/docker). Reconciled package root as `app/` and evaluation root as `evaluation/`. Reconciled `docs/decisions.md` as sole canonical ADR log. Executed baseline tool checks (`pytest`, `ruff`, `mypy`) and documented pre-existing failures. Created `docs/repository-map.md`. |

## Handoff Notes

- Current state: Scope complete and validated. `docs/repository-map.md` created.
- Remaining work: None for TASK-001.
- Exact next action: Proceed to parallel foundation tasks TASK-002 (Runtime profiles), TASK-003 (Frozen contracts), or TASK-006 (CI/quality gates).

## Definition of Done

DONE requires a reviewed repository map, reproducible baseline evidence, satisfied criteria, current dashboard/handoff, and no blocker. State verified and criteria satisfied.
