# TASK-019 â€” Integrate authenticated real-device gateway

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E4 â€” Integration
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-008, TASK-018; external hardware protocol/audio readiness
- **Requirement IDs:** FR-003, FR-004, FR-005, FR-022, SEC-002, SEC-004
- **Architecture/ADR:** Thin ESP32-S3 client and authoritative backend; ADR-003, ADR-014
- **Recommended agent capabilities:** `backend`, `integration`, `debugging`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Connect one authenticated ESP32-S3 through WebSocket, real audio framing, ACK/resend/resume, output commands, and local stop without changing domain policy.

## Context

Hardware integration must use frozen contracts and preserve simulators. Device credentials are unique/short-lived and no cloud provider secret lives on firmware.

## Scope

- Device auth/session token and WebSocket lifecycle.
- Validate real microphone frames; tune bounded chunks/buffer.
- Commands for audio/display/LED-or-servo/stop-cancel using versioned enums.
- Reconnect/resume and one bounded resend against real hardware.
- â‰¥30 scripted real-device turns.

## Out of Scope

- Firmware implementation ownership, Flutter, CV, hardware redesign.

## Relevant Architecture

- Backend FSM owns state; physical/guardian stop always available; simulator remains a contract substitute.

## Inputs

- Compatible firmware build, device credentials, protocol/audio fixtures, spoken E2E release.

## Expected Outputs

- Gateway/auth/command wiring, consumer contract fixtures, real-device E2E/fault report.

## Implementation Requirements

- Authenticate before session; enforce size/rate/sequence.
- Reconnect uses durable acknowledged state.
- Device output cannot bypass validated `ResponsePlan`.

## Files / Modules Likely Involved

- `app/api/websocket.py`, `app/api/auth.py`, `app/device_protocol/gateway.py`, `commands.py`, integration tests.

## Constraints

- Additive/versioned protocol changes only. No firmware secret/provider SDK coupling.

## Edge Cases

- Token expiry, network flap, duplicate ACK, device reboot, audio format mismatch, output ACK lost, stop while disconnected.

## Error Cases

- Auth/contract mismatch rejects safely; disconnect persists recoverable state; repeated ACK failure records undelivered and ends safely.

## Tests

- Consumer contract; auth; 30-turn run; packet loss/reorder/duplicate/reboot/reconnect; stop from active states; simulator regression.

## Evaluation

- Real-device completion/reconnect rate, duplicate side effects, p50/p95 latency, contract compatibility.

## Acceptance Criteria

- [ ] Authenticated device completes the pilot activity end to end.
- [ ] Invalid/revoked device cannot start session.
- [ ] Reconnect resumes last durable ACK state or safely restarts.
- [ ] Duplicate/reordered frames cause zero duplicate attempts/mastery/playback.
- [ ] Physical/device stop works without providers.
- [ ] Simulator remains runnable.

## Risks

- Late firmware drift; freeze consumer fixtures and require versioned negotiation.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting speech baseline and hardware.
- Remaining work: Entire scope.
- Exact next action: Run handshake/audio contract test against the target firmware before full E2E.

## Definition of Done

DONE requires real-device/fault evidence, simulator regression, satisfied criteria, and no blocker.