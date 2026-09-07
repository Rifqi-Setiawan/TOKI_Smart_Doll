# TASK-018 â€” Prove spoken activity, latency, and privacy

## Metadata

- **Status:** TODO
- **Priority:** P0
- **Epic:** E3 â€” Speech Baseline
- **Owner/Last Agent:** Unassigned
- **Dependencies:** TASK-013, TASK-015, TASK-016, TASK-017
- **Requirement IDs:** REL-008, OBS-001â€“004, SEC-007
- **Architecture/ADR:** Speech-enhanced deterministic slice; ADR-008, ADR-009, ADR-015
- **Recommended agent capabilities:** `evaluation`, `backend`, `testing`
- **Suggested execution order:** Execute after every listed task dependency is `DONE`; follow the critical/parallel lane in `tasks/index.md`.

## Objective

Complete the same pilot activity from frozen/live speech to audible response, measure endpoint-to-first-audio by stage, and prove privacy-safe degradation to deterministic/cached behavior.

## Context

Speech changes perception/rendering only; state, assessment, safety, persistence, and fallback remain deterministic.

## Scope

- Wire audioâ†’ASRâ†’assessor/plannerâ†’cache/TTS using public contracts.
- E2E tests for expected, silence, uncertain, ASR timeout, TTS failure.
- Per-stage root trace, latency/cost/cache/fallback metrics, privacy scan.
- Preserve deterministic text/cached demo when speech providers disabled.

## Out of Scope

- Real ESP32 transport, optional semantic resolver/paraphraser, performance optimization beyond blocking defects.

## Relevant Architecture

- p95 endpoint-to-first-audio target â‰¤3 seconds; uncertainty never child error; fixed audio cache-first.

## Inputs

- Frozen audio fixtures, ASR/TTS adapters, deterministic slice, observability.

## Expected Outputs

- Spoken E2E suite, runnable demo, latency breakdown report, privacy/failure evidence.

## Implementation Requirements

- Use final ASR evidence for learning commit; partials cannot update mastery.
- Trace IDs correlate audio, ASR, assessment, plan, render, and durable event.
- Report honest p50/p95 and bottleneck if target misses.

## Files / Modules Likely Involved

- Orchestrator speech wiring, telemetry spans, `tests/e2e/test_spoken_activity.py`, evaluation report.

## Constraints

- No unrestricted transcript/raw media in normal telemetry. No model retry on identical input.

## Edge Cases

- Late final after timeout, partial/final conflict, echo-like fixture, silence then stop, cache corruption.

## Error Cases

- Every provider/input failure returns a bounded plan/fallback and consistent durable outcome.

## Tests

- Frozen spoken happy/uncertain/silence/provider-failure cases; latency instrumentation; provider-off bypass; privacy/log scan; stale final rejection.

## Evaluation

- Completion/reprompt/fallback; p50/p95 by stage/end-to-first-audio; cache hit; cost; privacy findings.

## Acceptance Criteria

- [ ] Recorded/spoken expected answer completes without text injection.
- [ ] Silence/uncertainty/timeouts never record child incorrectness.
- [ ] Fixed content plays without online TTS.
- [ ] p95 â‰¤3 seconds is measured, or decomposed miss is documented for TASK-026 without hiding it.
- [ ] Provider-off deterministic demo remains operational.
- [ ] Privacy scan has zero critical findings.

## Risks

- Provider/network variability; capture distributions and retain the deterministic/cached baseline.

## Work Log

| Date (UTC) | Agent | Commit | Work / evidence |
|---|---|---|---|
| 2026-09-06 | Planning agent | â€” | Initial task created. |

## Handoff Notes

- Current state: Awaiting speech components.
- Remaining work: Entire scope.
- Exact next action: Run one frozen audio happy path and verify stage trace before expanding failure cases.

## Definition of Done

DONE requires reproducible spoken/failure/privacy evidence, latency report, satisfied criteria, and no blocker.