# Agent Operating Contract

## Source of truth

The authoritative project state is:

- docs/architecture.md
- docs/requirements.md
- docs/decisions.md
- docs/roadmap.md
- tasks/current.md
- handoffs/latest.md

Conversation history is NOT authoritative.

# Multi-Agent Repository Rules

This repository is the source of truth for Codex, Kiro, Antigravity, and future coding agents. Conversation history is non-authoritative.

## Source-of-truth order

## Before working

1. Read `AGENTS.md`, `CURRENT_TASK.md`, `handoffs/latest.md`, and the active `tasks/TASK-XXX.md`.
2. Read every requirement and architecture/ADR reference named by the task.
3. Inspect `git status`, current branch, latest commit, and relevant existing tests.
4. Confirm all dependencies are `DONE`; otherwise mark the task `BLOCKED` and record the exact blocker.
5. Set the task to `IN_PROGRESS`, record the agent and starting commit, and update `CURRENT_TASK.md`.

## During work

- Work on one coherent task. Do not silently expand scope.
- Keep the previous runnable path until the new path passes its gate.
- Add tests with behavior; do not postpone validation to a later agent.
- Reference requirement IDs in commits/PRs and task work logs.
- Record material discoveries, decisions, commands, and blockers in repository files before ending a session.
- Never silently change architecture. Propose an ADR in `docs/decisions.md`; do not implement the change until accepted.
- Never let AI/provider output directly mutate state, mastery, safety policy, persistence, or device commands.
- Never add secrets, raw child media, direct child identifiers, unrestricted transcripts, or provider payloads to normal logs or fixtures.
- Do not mark `DONE` because code was generated or appears plausible.

## Before handoff

1. Stop at a coherent, recoverable point.
2. Run the task's required tests/evaluations, or record why they could not run.
3. Update the task work log, checked acceptance criteria, remaining work, and exact next action.
4. Replace `handoffs/latest.md` with the current state and archive the previous handoff under `handoffs/history/`.
5. Update `CURRENT_TASK.md` and `tasks/index.md` consistently.
6. Record branch, commit, and working-tree status; never claim a clean tree without checking it.

## Before marking REVIEW

- Implementation scope is complete.
- Required automated tests pass.
- Required evaluation artifacts exist and are reproducible.
- Acceptance criteria are checked with evidence links/commands.
- Docs/contracts/migrations and rollback notes are current.
- Known residual risks are explicit; there is no hidden blocker.

## Before marking DONE

- A reviewer or separate validation pass confirms the behavior, tests, evaluation, and acceptance evidence.
- All Definition of Done conditions in the task file are satisfied.
- No unresolved blocker remains.
- `tasks/index.md`, the task file, `CURRENT_TASK.md`, and handoff state agree.
- Architecture-impacting changes have an accepted ADR.

## Status transitions

`TODO -> READY -> IN_PROGRESS -> REVIEW -> DONE`

Use `BLOCKED` from `READY` or `IN_PROGRESS` when an external or prerequisite condition prevents safe progress. Return to `READY` once resolved. Reopening a `DONE` task requires a work-log entry and reason.

## Manual capability routing

Choose an agent based on verified capabilities and current repository access, not brand. Match the task's `Recommended agent capabilities`, prefer the agent that can run the required validation locally, and use a second agent/reviewer for high-risk architecture, security, safety, migration, or AI promotion decisions. Do not add an automated router before manual routing creates a measurable coordination bottleneck.

### Capability routing matrix

| Capability | Use when the task primarily needs | Required evidence before handoff |
|---|---|---|
| `repository_inspection` | Existing-code discovery, dependency mapping, git/repository state | File/module map and reproducible baseline commands |
| `implementation` | A bounded behavior with frozen contracts | Focused diff, tests, acceptance evidence |
| `debugging` | Reproduction and root-cause isolation | Minimal reproduction, cause, regression test |
| `testing` | Unit/contract/integration/E2E/failure validation | Commands, versions, results, failing artifacts |
| `refactoring` | Behavior-preserving structural improvement | Before/after tests and bounded rollback |
| `frontend` | Flutter/dashboard consumer behavior | Contract fixtures, UI test, privacy/accessibility check |
| `backend` | FastAPI, orchestration, protocol, persistence, APIs | Type/contract/integration tests and trace evidence |
| `AI_ML` | ASR/semantic/TTS/CV adapters or model experiments | Versioned dataset, sliced metrics, fallback and ablation |
| `evaluation` | Dataset, scorers, baselines, promotion/release gates | Reproducible scorecard and manifest |
| `infrastructure` | Containers, profiles, CI, cloud/local parity, demo startup | Clean-build/start/health/recovery evidence |
| `documentation` | Contracts, runbooks, task/handoff/ADR state | Links validated against repository behavior |
| `architecture_review` | Dependency direction or proposed ADR | Options/trade-offs, requirement impact, tests, rollback |

### Selecting Codex, Kiro, Antigravity, or another agent

1. Filter candidates by access: repository, terminal, required provider/hardware environment, and ability to execute the task's validation.
2. Match the task's required capabilities to demonstrated strengths for this repository; do not infer capability from product name alone.
3. Prefer continuity only when the handoff is current; otherwise prefer the agent best able to inspect and validate from scratch.
4. Assign a separate reviewer/validation pass for architecture, migration, auth/privacy/safety, AI promotion, and release-gate tasks.
5. Record the selected agent in the task and `CURRENT_TASK.md`. Re-route manually when blocked and archive a handoff first.