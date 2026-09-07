# TASK-017 â€” Implement cache-first Indonesian audio rendering

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E3 â€” Speech Baseline
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-005, TASK-011, TASK-014
- **Requirement IDs:** FR-013, REL-007, AI-006
- **Architecture/ADR:** Cache-first supported Indonesian TTS; ADR-007, ADR-009
- **Recommended agent capabilities:** `backend`, `AI_ML`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Render validated response plans through cached/pre-generated audio first and a supported `id-ID` TTS adapter only where explicitly dynamic.

## Context

Fixed prompts, feedback, safety, and stop messages must work without online TTS. XTTS-v2 is rejected for the Indonesian baseline.

## Scope

- Versioned audio-asset manifest and integrity checks.
- Cache lookup/streaming and supported Indonesian TTS adapter for approved cache misses.
- Fallback order: exact asset â†’ managed TTS for approved text â†’ generic reviewed asset â†’ safe pause/stop.
- First-audio/cost/cache metrics.

## Out of Scope

- Voice cloning, XTTS-v2, arbitrary text synthesis, final device playback transport.

## Relevant Architecture

- TTS receives only final validated plan text; dynamic provider is replaceable and bounded.

## Inputs

- Approved templates/cache IDs, pronunciation reviewer, provider credentials/voice availability.

## Expected Outputs

- Audio cache/manifest, renderer, TTS adapter, pre-generated pilot assets, fallback tests, spot-check report.

## Implementation Requirements

- Verify asset digest/format/version; stream first chunk if supported.
- Never synthesize unapproved/unvalidated text.
- Pin voice/provider; normalized timeout/error; no repeated model retry.

## Files / Modules Likely Involved

- `app/speech/tts/`, `audio_cache.py`, `app/response/audio_renderer.py`, `assets/audio/manifest.*`, tests/reports.

## Constraints

- Common path must be offline-capable. No child voice cloning.

## Edge Cases

- Missing/corrupt asset, duplicate text with version change, unsupported voice, TTS timeout, stream interruption.

## Error Cases

- Corrupt/missing/dynamic failure follows reviewed fallback order and records reason; no invalid audio command.

## Tests

- Cache hit/miss/digest/corruption; TTS contract/failure; fallback ordering; unapproved-text rejection; first-chunk behavior.

## Evaluation

- Pronunciation/intelligibility review, cache-hit rate, first-audio p50/p95, provider cost/failure rate.

## Acceptance Criteria

- [ ] All pilot fixed/safety/stop prompts resolve from verified cache.
- [ ] Cache hits make zero provider calls.
- [ ] Dynamic TTS only accepts approved validated text.
- [ ] Provider/cache failures end in a reviewed valid fallback.
- [ ] Voice/version and pronunciation review are recorded.

## Risks

- Voice availability changes; pin release assets and retain adapter/fallback.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting approved templates/assets.
- Remaining work: Entire scope.
- Exact next action: Freeze asset manifest schema and enumerate every pilot response plan.

## Definition of Done

DONE requires cache/fallback/provider tests, pronunciation evidence, satisfied criteria, and no blocker.