# TASK-015 â€” Implement bounded audio ingestion

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E3 â€” Speech Baseline
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-003, TASK-008, TASK-014
- **Requirement IDs:** API-002, SEC-003, DATA-006
- **Architecture/ADR:** Transient bounded audio path; ADR-008, ADR-013
- **Recommended agent capabilities:** `backend`, `testing`, `security`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Accept validated binary audio chunks and explicit `audio.end`, assemble one bounded transient turn buffer, and hand it to ASR without retaining raw media.

## Context

Audio is separate from JSON control metadata and is child-sensitive. Limits must apply before expensive processing.

## Scope

- Codec/sample-rate/channel/chunk/duration/size negotiation and validation.
- Turn-scoped buffering, ordering, cancellation, cleanup, and explicit endpoint signal.
- Rate/size limits and transient-storage lifecycle.
- Test/debug text path limited to non-production profiles.

## Out of Scope

- VAD tuning, ASR provider, long-term audio storage, streaming model selection.

## Relevant Architecture

- Protocol envelope correlates binary frames to session/turn/sequence; raw media ephemeral by default.

## Inputs

- Audio/device contract and representative safe fixtures.

## Expected Outputs

- Audio ingestion/buffer service, validated metadata, cleanup policy, security/privacy tests.

## Implementation Requirements

- Reject over-limit/mismatched frames before allocation/provider call.
- Delete buffers on completion, timeout, cancellation, and process recovery according to bounded policy.
- Logs contain duration/status/reason only, not audio bytes/unrestricted transcript.

## Files / Modules Likely Involved

- `app/speech/ingestion.py`, `audio_contracts.py`, protocol gateway, tests/privacy fixtures.

## Constraints

- No continuous cloud audio; no retained normal-profile raw audio.

## Edge Cases

- Missing/out-of-order chunk, duplicate chunk, early `audio.end`, zero-length audio, disconnect, oversized declaration vs bytes.

## Error Cases

- Invalid/expired audio returns typed rejection, cleans buffer, and cannot trigger ASR or child penalty.

## Tests

- Format/limit/order/duplicate/cancel/cleanup tests; memory bound; privacy/log scan; non-prod debug route restriction.

## Evaluation

- Buffer latency/memory by max allowed input; zero retained media after lifecycle tests.

## Acceptance Criteria

- [ ] Valid fixture produces exactly one bounded ASR input.
- [ ] Invalid/oversized/reordered input is rejected before provider work.
- [ ] Buffers clean up on every terminal/error path.
- [ ] Normal logs/storage contain no raw audio.
- [ ] Production profile exposes no text bypass.

## Risks

- Hardware format mismatch; freeze fixtures and revalidate with device in TASK-019.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting deterministic slice.
- Remaining work: Entire scope.
- Exact next action: Confirm hardware audio envelope and implement limit-first validation tests.

## Definition of Done

DONE requires validation/cleanup/privacy tests, measured resource bounds, satisfied criteria, and no blocker.