# TASK-009 — Implement approved curriculum access

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E2 — Deterministic Core
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-003, TASK-004
- **Requirement IDs:** FR-006, FR-007, DATA-003
- **Architecture/ADR:** Structured curriculum SQL; ADR-005
- **Recommended agent capabilities:** `backend`, `database`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Validate, version, approve, activate, and retrieve one curriculum activity with exact provenance using structured PostgreSQL lookup.

## Context

Curriculum constrains every child-facing turn. Draft/revoked content must never enter a live session, and five small modules do not justify vector RAG.

## Scope

- Activity schema: module, skill, difficulty, prompt, expected reply/answer spec, hints, retry/fallback, review status, audio IDs.
- Import validation and explicit immutable approval/version activation.
- Runtime lookup by active module/activity/skill and approved version.
- One reviewed pilot activity fixture.

## Out of Scope

- Authoring UI, automatic publication, vector search, multiple polished modules.

## Relevant Architecture

- Structured metadata lookup with exact content/version provenance.

## Inputs

- PAUD-reviewed activity/content/template/audio identifiers; contracts and DB models.

## Expected Outputs

- Curriculum models/service/importer/approval flow, seed fixture, provenance DTO, tests.

## Implementation Requirements

- Approved version immutable; edits create new version and review trail.
- Runtime service rejects draft, revoked, missing, or version-mismatched content.
- Import is idempotent and reports field-level errors.

## Files / Modules Likely Involved

- `app/curriculum/models.py`, `service.py`, `importer.py`, `approval.py`, fixtures, tests.

## Constraints

- No model-generated facts or automatic approval. No ChromaDB/pgvector.

## Edge Cases

- Duplicate import, active version revoked mid-session, missing audio asset, unsupported answer spec, concurrent activation.

## Error Cases

- Invalid/unapproved content fails closed with typed error; active session retains pinned approved version or ends safely.

## Tests

- Schema round-trip, import validation/idempotency, immutability, approval/activation, draft/revoked rejection, pinned-version retrieval.

## Evaluation

- 100% provenance and validation on pilot pack; qualified content review is external evidence.

## Acceptance Criteria

- [ ] One complete reviewed activity validates and round-trips.
- [ ] Only approved active/pinned versions are served.
- [ ] Changes create a new immutable version with reviewer provenance.
- [ ] Every retrieved item includes content/version IDs and existing cache references.
- [ ] Import and rejection tests pass.

## Risks

- Content review delay; use one clearly reviewed pilot pack and keep imports additive.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | — | Initial task created. |

## Handoff Notes

- Current state: Awaiting contracts/database and reviewer input.
- Remaining work: Entire scope.
- Exact next action: Validate the smallest activity schema with the curriculum owner.

## Definition of Done

DONE requires approval/provenance tests, reviewed pilot evidence, satisfied criteria, and no blocker.
