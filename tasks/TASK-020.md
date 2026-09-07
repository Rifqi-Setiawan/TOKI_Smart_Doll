# TASK-020 â€” Integrate guardian consent and Flutter progress API

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E4 â€” Integration
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-013, TASK-019; external Flutter contract readiness
- **Requirement IDs:** FR-003, FR-016, DATA-008, DATA-009, DATA-010, SEC-001, SEC-008
- **Architecture/ADR:** Guardian-controlled non-clinical progress; ADR-001, ADR-013
- **Recommended agent capabilities:** `backend`, `security`, `integration`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Expose authenticated, resource-authorized consent/profile/session/progress APIs and prove one device attempt appears correctly in Flutter.

## Context

Parent monitoring is secondary but essential for consent and interpretable learning evidence. It must never expose another child, raw media, or clinical claims.

## Scope

- Guardian authentication integration and resource-level authorization.
- Consent create/read/revoke and session-start enforcement.
- Pseudonymous child age-band profile; session/attempt/mastery explanation/progress endpoints.
- Role matrix for guardian/content reviewer/operator/admin.
- Flutter consumer contract test and real integration scenario.

## Out of Scope

- Flutter UI ownership, research-media upload workflow, diagnostic dashboards, delete/export execution beyond defined behavior/contract.

## Relevant Architecture

- Approved consent required before session; progress derived from durable events and distinguishes uncertainty.

## Inputs

- Auth provider/config, progress DTOs, consent policy, Flutter fixtures.

## Expected Outputs

- Auth/authorization/consent endpoints, role policy, Flutter contract fixtures/tests, API docs.

## Implementation Requirements

- Revocation immediately prevents new sessions.
- Cross-guardian resource access fails uniformly without information leak.
- Responses use non-clinical language and expose provenance/explanation, not raw transcript/media.

## Files / Modules Likely Involved

- `app/api/auth.py`, `consent.py`, `progress.py`, security policy, contract/integration tests.

## Constraints

- Minimum roles enforced. Exact DOB/direct identifiers avoided where unnecessary.

## Edge Cases

- Revocation during session, multiple guardians, stale projection, deleted/expired link, role change, empty history.

## Error Cases

- Unauthorized/not-linked access rejected with typed non-leaking response; stale progress reports timestamp/pending state.

## Tests

- Auth matrix/cross-guardian access; consent start/revoke; role tests; non-clinical response snapshots; Flutter consumer; deviceâ†’projectionâ†’Flutter E2E.

## Evaluation

- Authorization pass/fail matrix, projection-to-Flutter lag, DTO compatibility, zero privacy findings.

## Acceptance Criteria

- [ ] Active authenticated consent is required for session start.
- [ ] Revocation blocks all new sessions.
- [ ] Cross-guardian tests always fail without leakage.
- [ ] One real-device attempt appears accurately in Flutter with uncertainty/provenance intact.
- [ ] API contains no diagnosis/raw media/direct identifier in normal response.

## Risks

- Auth integration delays core demo; keep simulator contract and minimal secure UI surface.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting device/progress path and Flutter contract.
- Remaining work: Entire scope.
- Exact next action: Freeze authorization matrix and consent lifecycle tests before endpoint wiring.

## Definition of Done

DONE requires auth/consent/Flutter/privacy tests, API docs, satisfied criteria, and no blocker.