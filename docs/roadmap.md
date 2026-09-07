# TOKI Backend & Conversational AI — Implementation Roadmap

**Competition:** LIDM 2026 — Inovasi Teknologi Digital Pendidikan  
**Final demonstration:** 2–4 November 2026  
**Subsystem owner:** Backend & Conversational AI Developer  
**Roadmap status:** implementation plan derived from the target architecture; no implementation code included

## 1. Scope and planning assumptions

This roadmap covers the subsystem directly owned by the Backend & Conversational AI Developer:

- FastAPI REST and WebSocket gateway;
- device protocol validation, sequencing, acknowledgement, and reconnect behavior;
- deterministic session state machine and orchestration;
- PostgreSQL schema, repositories, transactions, append-only events, and outbox;
- curriculum/content access and deterministic answer assessment;
- ASR, bounded semantic resolution, constrained LLM paraphrasing, safety validation, and TTS;
- response planning, cached audio, and safe fallback behavior;
- parent-facing progress API contracts;
- observability and evaluation replay integration.

The following are integration dependencies, not primary ownership:

- ESP32-S3 firmware, microphone/camera/speaker implementation;
- CV model implementation and calibration;
- Flutter UI;
- curriculum and child-development validation;
- BKT or other learned mastery modeling.

### Explicit architecture decisions carried into the roadmap

1. Use a modular monolith, not microservices.
2. Use an explicit deterministic state machine; there are no runtime agents.
3. PostgreSQL is the authoritative store; in-process state is only a cache.
4. AI outputs are typed evidence or wording candidates, never direct state mutations.
5. Structured curriculum lookup replaces vector RAG for the first production path.
6. Low-confidence ASR/semantic results become `UNCERTAIN` or `ABSTAIN`, not `INCORRECT`.
7. Fixed prompts and safety messages use cached/pre-generated audio.
8. The same container must run in cloud and on the local demo laptop.
9. Raw child audio/video is ephemeral by default and excluded from normal logs.

### Repository caveat

No TOKI repository tree was available during preparation. The module paths below are therefore the target package boundaries from the approved architecture. If the repository already uses different names, preserve its conventions and map these responsibilities into existing modules instead of performing a cosmetic restructure.

## 2. Delivery strategy

Every phase must satisfy all four invariants:

1. `main` remains buildable and tests remain green.
2. New behavior is hidden behind a feature flag, adapter, or backwards-compatible contract until complete.
3. The previous working path remains available until the replacement passes its exit gate.
4. Each phase ends with a recorded demo scenario, evaluation result, or both.

### Vertical-slice progression

| Phase | Demonstrable capability at phase exit | AI dependency required? |
|---|---|---|
| 0 | Service boots, DB migrates, contracts validate, simulators connect | No |
| 1 | One complete activity runs using text input and cached audio | No |
| 2 | The same activity accepts speech and speaks a response | ASR/TTS only |
| 3 | Device, Flutter, curriculum, and optional CV integrate through frozen contracts | ASR/TTS |
| 4 | Quality, latency, safety, and reliability are reproducibly measured | Only for evaluated paths |
| 5 | Measured bottlenecks improve; bounded LLM is enabled only if it wins | Conditional |
| 6 | The activity survives provider, internet, DB, and device failures safely | No external AI for fallback |
| 7 | A rehearsed competition demo runs in cloud and local/offline modes | Optional online AI |

### Suggested calendar allocation

Given the 2–4 November 2026 final, use overlapping calendar windows but sequential release gates:

| Calendar window | Primary phase | Decision point |
|---|---|---|
| 6–10 Sep | Phase 0 | Contracts and one module skeleton frozen |
| 11–18 Sep | Phase 1 | Deterministic vertical slice accepted |
| 19–27 Sep | Phase 2 | ASR/TTS baseline accepted and measured |
| 28 Sep–7 Oct | Phase 3 | Cross-team integration contract tests pass |
| 8–14 Oct | Phase 4 | Baseline report and frozen test sets complete |
| 15–21 Oct | Phase 5 | Keep/remove decisions for optional AI finalized |
| 22–27 Oct | Phase 6 | Failure-injection and offline demo gates pass |
| 28 Oct–1 Nov | Phase 7 | Code/config freeze and rehearsals |

Cross-team contract negotiation, consented audio collection, curriculum review, and cached-audio preparation should begin in Phase 0 and continue in parallel because they are schedule-critical dependencies.

## 3. Phase 0 — Repository and project foundation

### Goal

Create a reproducible, typed, observable project skeleton and freeze the minimum contracts needed for independent team development.

### Tasks

- Inventory the existing repository before restructuring; record current entry points, tests, configuration, and migrations.
- Establish modular-monolith package boundaries and dependency direction.
- Add one local startup path for API + PostgreSQL and a production-like container entry point.
- Add settings profiles for `test`, `local`, `cloud`, and `demo_offline`; secrets must remain external.
- Define versioned Pydantic contracts for device envelopes, session commands/events, ASR evidence, assessment, response plans, TTS output, CV observations, and progress DTOs.
- Define the state/event vocabulary and an initial transition table.
- Define correlation identifiers: `session_id`, `turn_id`, `trace_id`, `device_id`, `seq`, and `state_version`.
- Create initial Alembic migrations for devices, sessions, turns/attempts, curriculum versions, append-only events, and outbox records.
- Add provider interfaces plus deterministic fake adapters for ASR, TTS, semantic resolution, LLM paraphrasing, and CV.
- Add hardware and Flutter contract simulators so backend progress is not blocked by other teams.
- Encode one thin curriculum module with one activity, approved template text, expected answer specification, and cached audio identifiers.
- Configure CI for formatting/linting, type checking, unit tests, migration-up/down validation, and secret scanning.
- Write Architecture Decision Records for no runtime agents, no initial vector database, raw-media minimization, and local demo twin.

### Files/modules likely involved

```text
pyproject.toml
Dockerfile
compose.yaml
.env.example
alembic.ini
app/main.py
app/config/
app/api/
app/device_protocol/contracts.py
app/sessions/contracts.py
app/sessions/states.py
app/understanding/contracts.py
app/response/contracts.py
app/speech/interfaces.py
app/vision/interfaces.py
app/persistence/models.py
app/persistence/migrations/
app/telemetry/
tests/contract/
tests/fixtures/
docs/adr/
```

### Dependencies

- Hardware team: codec, sample rate, chunk size, event envelope, reconnect and ACK expectations.
- Flutter team: authentication assumptions and progress/session DTO needs.
- Curriculum/PAUD reviewer: one approved activity and allowed response templates.
- CV team: provisional observation schema; model is not required yet.
- Team decision: named owner for mastery rules.

### Tests

- Application boot and `/health/live` smoke test.
- Fresh-database migration and migration rollback test.
- JSON Schema/Pydantic round-trip tests for every external contract.
- Contract version rejection and unknown-field policy tests.
- Fake-provider tests proving adapters can be replaced without changing orchestration code.
- Architectural dependency test preventing API/provider modules from bypassing domain interfaces.

### Evaluation

- Measure clean checkout-to-running-service time.
- Count unresolved fields in each cross-team contract.
- Track CI duration and test flakiness from the first merge.

### Acceptance criteria

- A clean checkout starts the service and database with one documented command.
- All migrations apply to an empty database in CI.
- Hardware and Flutter simulators complete a handshake using versioned contracts.
- One sample curriculum item validates and references an existing cached-audio asset.
- All provider dependencies can be replaced by deterministic fakes.
- No secret, raw audio, or child PII is committed or emitted by smoke tests.

### Risks

- Premature restructuring could conflict with existing code. Mitigation: inventory first and migrate incrementally.
- Contract debates can block coding. Mitigation: freeze a minimal `v1` and record additive follow-ups.
- Cross-team schemas may drift. Mitigation: publish JSON fixtures and run consumer contract tests in CI.

### Working-state checkpoint

Demo the API booting, a simulated device connecting, a sample event being validated, and a database event appearing with trace identifiers. No AI or real hardware is required.

## 4. Phase 1 — Deterministic core vertical slice

### Goal

Complete one learning activity end to end without external AI: session start → prompt → simulated text answer → assessment → feedback → evidence persistence → progress read.

### Tasks

- Implement the session state machine with explicit legal transitions, guards, timeouts, retry counters, and terminal states.
- Use optimistic concurrency on `state_version`; discard stale callbacks/events.
- Implement idempotency and sequence de-duplication for device messages.
- Implement structured curriculum lookup by approved version/module/activity/item.
- Implement deterministic answer assessment for exact phrases, normalized phrases, synonyms, silence, and unrelated input.
- Implement `CORRECT`, `INCORRECT`, `UNCERTAIN`, and `NO_SPEECH` semantics; only sufficient evidence may produce `INCORRECT`.
- Implement a deterministic response planner selecting pedagogical act, text/template ID, cached audio ID, and device gesture.
- Implement primary safety rules and canned escalation selection before any generative model exists.
- Persist the session transition, attempt evidence, response plan, and outbox event transactionally.
- Implement a minimal parent progress/session summary read API.
- Add structured logs and one trace per turn with redaction.

### Files/modules likely involved

```text
app/sessions/orchestrator.py
app/sessions/state_machine.py
app/sessions/policies.py
app/curriculum/service.py
app/curriculum/models.py
app/understanding/normalization.py
app/understanding/deterministic_assessor.py
app/response/planner.py
app/safety/policy.py
app/safety/catalog.py
app/mastery/rules.py
app/persistence/repositories/
app/persistence/unit_of_work.py
app/persistence/outbox.py
app/analytics/projections.py
app/api/sessions.py
app/api/progress.py
tests/unit/
tests/integration/
```

### Dependencies

- Phase 0 contracts and database foundation.
- One approved curriculum activity, expected-answer specification, and cached prompt/feedback audio.
- Provisional transparent mastery rule approved by the pedagogical owner.

### Tests

- Table-driven unit tests for every state/event pair and guard.
- Property/invariant tests: one active turn, monotonic `state_version`, no stale-result transition, no low-confidence `INCORRECT`.
- Answer normalization tests for casing, punctuation, common Indonesian variants, synonyms, silence, and off-topic text.
- Transaction rollback tests covering state, attempt, event, mastery, and outbox atomicity.
- Idempotency tests for duplicate device sequences and duplicate API requests.
- Safety policy tests for all initial high-severity categories.
- End-to-end API test using fake providers and a real test database.

### Evaluation

- 100% transition coverage for the implemented activity.
- Deterministic answer accuracy on the initial labeled intent/answer fixture.
- p50/p95 server-side orchestration latency excluding network and audio providers.
- Progress projection consistency against append-only events.

### Acceptance criteria

- The complete sample activity succeeds through the text/device simulator.
- Illegal or duplicate events cannot advance state twice.
- `UNCERTAIN` causes a reviewed retry/rephrase; it never records the child as wrong.
- Every child-facing response references an approved curriculum version and content/template ID.
- A completed attempt and parent progress summary are queryable after restart.
- Deterministic orchestration and persistence p95 is below 150 ms in the local benchmark.

### Risks

- State-machine scope can expand into every future feature. Mitigation: support only one complete activity and named exceptional paths.
- Curriculum content may not be ready. Mitigation: use a clearly marked reviewed pilot pack, never model-generated facts.
- Mastery ownership may remain ambiguous. Mitigation: store neutral attempt evidence first; keep progression rules replaceable.

### Working-state checkpoint

Demo a complete interaction from a browser/CLI device simulator and show the persisted attempt in the progress endpoint. This is the first fully functional partial demo.

## 5. Phase 2 — Simplest working AI baseline

### Goal

Replace simulated text with real speech input and audible output while keeping control, assessment, safety, and fallbacks deterministic.

### Tasks

- Implement audio metadata and chunk validation, turn buffering, and explicit `audio.end` handling.
- Integrate one primary managed ASR provider through the normalized `ASRResult` contract.
- Record hypotheses, confidence/evidence metadata, provider/model version, timing, and abstention reason without storing raw audio in normal telemetry.
- Define ASR deadline and map timeout/invalid output to `ABSTAIN`.
- Integrate one supported Indonesian TTS provider behind the audio-renderer interface.
- Route fixed content to pre-generated/cached audio; call dynamic TTS only on cache miss or explicitly dynamic content.
- Stream the first audio chunk when supported and record endpoint-to-first-audio latency.
- Build a small consented device-recorded evaluation set covering expected words, noise, distance, and several speakers; use adult simulation until child-data approval exists.
- Keep semantic resolver and LLM paraphraser disabled by default.
- Implement a text-input debug route only in development/test profiles so the deterministic path remains easy to diagnose.

### Files/modules likely involved

```text
app/speech/ingestion.py
app/speech/audio_contracts.py
app/speech/asr/base.py
app/speech/asr/<provider>.py
app/speech/tts/base.py
app/speech/tts/<provider>.py
app/speech/audio_cache.py
app/understanding/asr_evidence.py
app/response/audio_renderer.py
app/config/providers.py
app/telemetry/spans.py
app/evaluation/asr_replay.py
tests/provider_contract/
tests/e2e/test_spoken_activity.py
```

### Dependencies

- Phase 1 deterministic activity loop.
- Provider credentials, quotas, model/voice availability, and data-processing review.
- Hardware/device microphone recordings and agreed audio format.
- Approved retention and consent rules for evaluation recordings.

### Tests

- Audio codec/rate/channel/size validation tests.
- ASR/TTS provider contract tests using recorded fixtures and stubbed provider failures.
- Cache hit/miss and corrupted-asset tests.
- Timeout, empty transcript, invalid confidence, and provider-schema drift tests.
- End-to-end spoken activity test on CI using a frozen audio fixture.
- Privacy test asserting raw audio and unrestricted transcripts do not enter ordinary logs.

### Evaluation

- ASR: WER, CER, concept accuracy, and abstention rate, sliced by noise/distance/speaker.
- End to end: task completion, reprompt rate, p50/p95 endpoint-to-first-audio latency.
- TTS: pronunciation spot check, intelligibility review, cache-hit rate, first-audio latency.
- Cost per completed activity and provider failure rate.

### Acceptance criteria

- A real recorded/spoken expected answer completes the Phase 1 activity without text injection.
- Fixed prompts and standard feedback play from cache with no online TTS dependency.
- ASR timeout, silence, or uncertainty leads to a safe retry/fallback and no false child error.
- All provider outputs validate against internal contracts before use.
- Measured p95 endpoint-to-first-audio is recorded; initial target is ≤3 seconds, with any miss decomposed by trace stage.
- The deterministic text/cached-audio demo remains operational if ASR/TTS is disabled.

### Risks

- Child Indonesian speech may perform much worse than adult speech. Mitigation: report slices honestly and prioritize concept accuracy plus abstention.
- TTS voice/model availability can change. Mitigation: adapter boundary and pre-generated fixed assets.
- Provider latency can dominate. Mitigation: strict deadlines, streaming, short responses, and cache-first rendering.

### Working-state checkpoint

Demo the same single activity with live speech and spoken feedback, then toggle ASR failure to show a controlled reprompt using cached audio.

## 6. Phase 3 — Cross-team integration

### Goal

Connect real hardware, Flutter, curriculum content, mastery rules, and optional CV through versioned interfaces without coupling their release schedules.

### Tasks

- Integrate device authentication, WebSocket lifecycle, monotonic sequence handling, ACK/resend, and reconnect/resume behavior.
- Validate the real microphone stream against the frozen audio envelope and tune chunk/buffer limits.
- Add device output commands for audio, display, LED/servo gesture, and stop/cancel.
- Publish and test authenticated parent APIs for consent/profile, session summaries, attempts, mastery explanation, and progress.
- Add curriculum import/validation and explicit approval/version activation; reject draft/unapproved content at runtime.
- Integrate rule-based mastery through neutral learning-evidence events; isolate it behind an interface if another teammate owns the logic.
- Integrate the CV adapter asynchronously using a triggered snapshot and curated label vocabulary; CV timeout/`UNKNOWN` must not block the speech loop.
- Add an outbox consumer/projector so analytics updates do not extend the response critical path.
- Run a scheduled integration smoke test with real device + backend + Flutter at least daily.
- Maintain simulators and golden fixtures as substitutes for unavailable team components.

### Files/modules likely involved

```text
app/api/websocket.py
app/api/auth.py
app/api/progress.py
app/device_protocol/gateway.py
app/device_protocol/sequencing.py
app/device_protocol/commands.py
app/curriculum/importer.py
app/curriculum/validation.py
app/curriculum/approval.py
app/mastery/service.py
app/vision/adapter.py
app/vision/policy.py
app/analytics/projector.py
tests/contract/consumers/
tests/integration/device/
tests/integration/flutter/
tests/e2e/test_real_stack.py
```

### Dependencies

- Hardware firmware implementing the agreed envelope and ACK semantics.
- Flutter authentication and DTO consumers.
- Curriculum/PAUD-approved content pack.
- CV team output contract and confidence/unknown policy.
- Decision on mastery ownership and pedagogical parameters.

### Tests

- Consumer-driven contract tests for hardware, Flutter, curriculum importer, and CV.
- WebSocket disconnect/reconnect, duplicate frame, reordering, stale callback, and resume tests.
- Permission/consent tests for parent APIs and session start.
- Curriculum draft/unapproved/version-mismatch rejection tests.
- Async projection eventual-consistency and rebuild tests.
- End-to-end real-stack test for one complete activity.

### Evaluation

- Real device turn-completion rate across at least 30 scripted turns.
- Disconnect recovery rate and duplicate-side-effect count.
- Contract compatibility rate across team builds.
- Progress update lag from committed attempt to Flutter-visible projection.
- CV coverage/abstention recorded separately; no CV accuracy claim before Phase 4.

### Acceptance criteria

- One real device completes the activity and its evidence appears correctly in Flutter.
- Reconnect resumes from the last durable, device-acknowledged state or safely restarts the activity.
- Duplicate/reordered frames produce zero duplicate attempts or mastery updates.
- Only approved curriculum versions can be served.
- CV can be disabled, timeout, or return `UNKNOWN` without breaking the normal speech activity.
- Simulated integration remains runnable when hardware, Flutter, or CV is unavailable.

### Risks

- Interface changes near the deadline can destabilize all teams. Mitigation: additive versioning and published fixtures.
- Hardware audio behavior may invalidate provider benchmarks. Mitigation: rerun Phase 2 metrics with device-captured audio.
- Asynchronous projections may confuse demos. Mitigation: show pending/updated state and set a measured projection-lag SLO.

### Working-state checkpoint

Demo device speech input, backend decision trace, audible feedback, and the resulting progress update in Flutter. CV is an optional asynchronous addition, not a gate.

## 7. Phase 4 — Evaluation and release gates

### Goal

Turn the working system into measurable evidence and freeze the baselines needed to decide which optional AI features are justified.

### Tasks

- Freeze versioned datasets for ASR, intent/answer assessment, curriculum invariants, safety, and reliability replay.
- Create a release manifest containing code SHA, curriculum version, prompt version, provider/model versions, feature flags, and dataset versions.
- Implement deterministic replay from recorded audio/events with expected state, assessment, response plan, and fallback outcome.
- Establish three comparable configurations: deterministic text/cached baseline, speech hybrid baseline, and candidate bounded-AI path.
- Build safety scenarios covering private data, adult content, violence/danger, medical/diagnostic requests, manipulation, prompt injection, abuse disclosure, and repeated distress, including Indonesian slang and ASR-corrupted variants.
- Add failure injection for ASR, semantic/LLM, TTS, DB, network, CV, and device ACK behavior.
- Produce automated scorecards and regression thresholds in CI.
- Have two qualified reviewers independently rate curriculum fidelity, developmental appropriateness, and nuanced safety; adjudicate disagreements.

### Files/modules likely involved

```text
app/evaluation/replay.py
app/evaluation/scorers.py
app/evaluation/release_manifest.py
evaluation/datasets/asr/
evaluation/datasets/intent_answer/
evaluation/datasets/safety/
evaluation/datasets/reliability/
evaluation/configs/
evaluation/reports/
tests/failure_injection/
tests/regression/
```

### Dependencies

- Stable Phase 3 vertical slice.
- Ethically approved and consented data policy where real child speech is used.
- Reviewer availability and an adjudication rubric.
- Sufficient device-recorded examples under venue-like conditions.

### Tests

- Dataset schema, uniqueness, label completeness, and leakage checks.
- Replay determinism for non-provider components.
- Metric implementation tests using hand-computable fixtures.
- Release-manifest completeness and reproducibility tests.
- CI regression tests for safety, schema validity, latency budget, and fallback outcomes.

### Evaluation

- ASR: WER, CER, concept accuracy, abstention, and selective accuracy with coverage.
- Understanding: macro F1, false-incorrect rate, abstention precision/recall, confusion matrix.
- Response: schema validity, approved provenance, concision, age appropriateness, unsafe-output rate.
- End to end: task completion, hint/reprompt/fallback rates, p50/p95 latency, cost per completed activity.
- Reliability: safe terminal-state rate for each injected failure.
- Human evaluation: inter-rater agreement and adjudicated pass rate.

### Acceptance criteria

- Frozen, versioned evaluation sets and a reproducible baseline report exist.
- 100% of generated/selected responses in the suite have valid schema and approved provenance.
- Zero high-severity unsafe outputs occur in the named frozen safety suite.
- 100% of required escalation cases select the approved canned response.
- No low-confidence case is recorded as `INCORRECT`.
- Every failure-injection scenario reaches a defined safe state.
- Metric results are sliced; no aggregate-only claim is used for competition evidence.

### Risks

- Small or unrepresentative datasets can create false confidence. Mitigation: disclose coverage and slices, then prioritize high-risk additions.
- Evaluation may arrive too late to influence design. Mitigation: add small fixtures in earlier phases; Phase 4 freezes and expands them.
- LLM-as-judge can obscure safety failures. Mitigation: deterministic checks first and qualified human review for nuanced criteria.

### Working-state checkpoint

Demo the replay harness and evidence dashboard: one successful turn, one uncertain turn, and one dependency failure, each with trace, outcome, provenance, and latency.

## 8. Phase 5 — Evidence-driven optimization and bounded AI

### Goal

Improve only measured bottlenecks and enable optional AI only when it produces a statistically and operationally meaningful benefit over the frozen baseline.

### Tasks

- Profile p95 stage latency and optimize the dominant stages first.
- Increase cached/pre-generated audio coverage and prefetch the next approved prompt.
- Tune endpointing/VAD, chunk sizing, ASR deadline, retry count, and provider selection using device data.
- Expand deterministic normalization, synonyms, phonetic variants, and common intents based on observed errors.
- Implement a bounded semantic resolver only for unresolved eligible turns, returning a fixed schema and `ABSTAIN`.
- Optionally implement constrained LLM paraphrasing from an approved response plan; validate length, language, provenance, forbidden content, and allowed pedagogical act.
- Keep both optional AI capabilities behind independently controllable feature flags and call budgets.
- Run A/B replay and ablation against the deterministic/speech baseline.
- Add pgvector/semantic retrieval only if the structured curriculum corpus has outgrown direct lookup and retrieval evaluation demonstrates a material gain. Otherwise, do not build it.
- Record tokens, characters, audio seconds, latency, fallback cause, and cost per completed activity.

### Files/modules likely involved

```text
app/understanding/semantic_resolver.py
app/understanding/phonetic_rules.py
app/response/paraphraser.py
app/response/validators.py
app/speech/prefetch.py
app/config/feature_flags.py
app/config/budgets.py
app/telemetry/costs.py
evaluation/ablations/
tests/ai_contract/
tests/regression/test_optional_ai.py
```

### Dependencies

- Phase 4 frozen baselines and error analysis.
- Qualified review of prompts, response constraints, and safety behavior.
- Provider SDK support for typed/structured outputs.
- Representative ambiguous-turn examples.

### Tests

- Structured-output validation, timeout, malformed response, and stale-result tests.
- Prompt-injection and off-topic tests against the semantic/paraphrase path.
- Feature-flag tests proving immediate bypass to deterministic behavior.
- Per-session model-call and cost-budget tests.
- Regression tests ensuring AI cannot select activity, mutate mastery, bypass safety, or advance state.
- Performance tests comparing enabled/disabled paths.

### Evaluation

- Primary decision metric: completed learning-turn improvement on ambiguous inputs.
- Guardrails: false-incorrect rate, unsafe-output rate, provenance validity, p95 latency, fallback rate, and cost.
- Report coverage and selective accuracy, not accuracy alone.
- Compare deterministic-only, ASR hybrid, semantic resolver enabled, and paraphraser enabled as separate ablations.

### Acceptance criteria

- Optional AI ships only if it improves the named primary metric on the frozen set without violating safety and latency gates.
- Suggested initial promotion rule: ≥5 percentage-point absolute improvement in ambiguous-turn completion, zero high-severity safety regression, 100% valid schema/provenance, and total endpoint-to-first-audio p95 ≤3 seconds. Recalibrate the effect threshold if dataset confidence intervals show it is not defensible.
- Invalid, slow, unsafe, or uncertain AI output is discarded and the deterministic fallback remains successful.
- AI model calls remain outside exact-answer/common-intent paths.
- A rollback is possible by changing a feature flag, without schema rollback.

### Risks

- Optional AI may add sophistication without user value. Mitigation: enforce the promotion gate and remove failed experiments from the demo path.
- Optimization may overfit the frozen set. Mitigation: retain a small blinded holdout and venue-like sessions.
- Provider/model changes can invalidate results. Mitigation: freeze versions for release and rerun the gate after changes.

### Working-state checkpoint

Show the same ambiguous input with the optional resolver off and on, alongside measured improvement. If the AI does not pass the gate, demo the deterministic baseline and present the negative result as an evidence-based design decision.

## 9. Phase 6 — Reliability, privacy, and fallback hardening

### Goal

Guarantee that every dependency failure has a bounded, child-safe exit and that the full core activity remains demonstrable without internet access.

### Tasks

- Add strict per-stage deadlines, bounded retries with jitter where appropriate, and circuit breakers for external providers.
- Implement a local/offline activity pack containing curriculum, deterministic assessment, canned/cached audio, and local persistence.
- Add ASR-unavailable alternatives appropriate to the activity, such as controlled repeat or adult-assisted/button input; never silently mark failure as wrong.
- Add TTS fallback ordering: cached exact asset → reviewed generic asset → safe activity pause.
- Ensure LLM/semantic outage bypasses directly to deterministic behavior.
- Ensure CV timeout/unknown is ignored or causes a non-blocking retry; it cannot affect mastery directly.
- Add a bounded local event buffer for temporary DB unavailability, with idempotent replay and no raw media.
- Harden device reconnect/resume, ACK timeout, and undelivered-response tracking.
- Add authentication/authorization checks, rate limits, input-size limits, secret rotation procedure, and telemetry redaction tests.
- Create `/health/live`, `/health/ready`, and a one-command dependency/demo health report.
- Run 200-turn replay, 30-minute soak, packet-loss/network-outage tests, and repeated restart recovery.

### Files/modules likely involved

```text
app/resilience/deadlines.py
app/resilience/retry.py
app/resilience/circuit_breaker.py
app/resilience/offline_mode.py
app/persistence/local_buffer.py
app/device_protocol/recovery.py
app/safety/redaction.py
app/api/health.py
app/security/
demo/activity_pack/
scripts/demo_healthcheck.*
tests/failure_injection/
tests/soak/
tests/privacy/
```

### Dependencies

- Frozen curriculum/audio assets.
- Demo laptop capacity and local network configuration.
- Hardware support for cache/reconnect/local stop behavior.
- Agreed operational limits and incident owner during the demo.

### Tests

- Failure matrix covering timeout, malformed response, rate limit, provider outage, internet loss, DB loss, process restart, device disconnect, stale result, and cache corruption.
- 200-turn deterministic replay with zero state divergence.
- 30-minute soak with leak/resource monitoring.
- Idempotent buffer replay after DB restoration.
- Authorization, rate-limit, oversized-payload, and log-redaction tests.
- Cloud-to-local configuration parity smoke test using the same container image.

### Evaluation

- Safe terminal/recovery-state rate by injected failure.
- Offline core-activity completion rate.
- Reconnect recovery rate and duplicate-side-effect count.
- p95/p99 latency and resource usage during soak.
- Raw-media/PII leakage count in logs, traces, errors, and exported demo data.

### Acceptance criteria

- 100% of named failure-injection scenarios end in a defined safe state.
- One complete activity works with external ASR/LLM/TTS/CV disabled using the approved offline path.
- Provider outages never crash the process or leave a session indefinitely active.
- 200-turn replay has zero duplicate attempts, illegal transitions, or state divergence.
- 30-minute soak shows no unbounded memory/connection growth.
- Zero raw child media or direct identifiers appear in normal logs and traces.
- The health report identifies cloud, DB, provider, device, cache, and offline-pack status before rehearsal.

### Risks

- Offline behavior may become a second product. Mitigation: support one complete approved activity, not full feature parity.
- Retry logic can multiply latency and cost. Mitigation: one bounded retry only where it improves recovery; otherwise fail over immediately.
- Local/cloud configuration drift can surface at the venue. Mitigation: same image, migrations, fixtures, and health check in both environments.

### Working-state checkpoint

Disconnect the internet during a live rehearsal and complete the prepared activity using cached content/audio, then restore connectivity and show idempotent recovery.

## 10. Phase 7 — Competition demo readiness

### Goal

Freeze a reliable release, rehearse a short evidence-rich judge experience, and eliminate avoidable venue and operator failure.

### Tasks

- Freeze code, container digest, migrations, provider/model names, prompt versions, curriculum version, audio assets, feature flags, and device firmware.
- Create a release candidate only from a commit that passed Phases 4–6 gates.
- Provision primary and backup demo devices/components where feasible.
- Prepare a local router/hotspot, demo laptop server, database snapshot, offline activity pack, cached dashboard data, and power/cable checklist.
- Build a one-command startup and health-check flow with clear green/yellow/red output.
- Script the judge narrative: deterministic expected answer, bounded AI ambiguity, optional object snapshot, parent progress, provenance/trace, and graceful failure.
- Preload/warm required services and verify quotas/billing before each rehearsal.
- Rehearse normal, offline, provider-timeout, device-reconnect, and operator-reset scenarios.
- Define operator roles, recovery commands, maximum recovery time, and the decision rule for switching to offline mode.
- Capture a fallback video only as presentation insurance; do not substitute it for the live primary demo.
- Freeze competition metrics and claims so slides, dashboard, and spoken narrative use identical definitions.

### Files/modules likely involved

```text
demo/runbook.md
demo/script.md
demo/checklist.md
demo/fixtures/
demo/dashboard_snapshot/
deploy/cloud/
deploy/local/
scripts/start_demo.*
scripts/demo_healthcheck.*
scripts/reset_demo.*
release/manifest.json
release/evaluation_summary.md
```

### Dependencies

- Phase 6 release candidate.
- Hardware, Flutter, curriculum, and CV teams' frozen compatible versions.
- Confirmed venue assumptions, quotas, credentials, power, and network alternatives.
- Team rehearsal availability.

### Tests

- Clean-laptop installation/startup rehearsal.
- Full demo from cold start and from warm start.
- Five consecutive scripted runs with no manual database edits.
- Offline switch and recovery rehearsal.
- Backup device/component swap rehearsal.
- Time-boxed reset to known state.
- Final privacy inspection of displayed logs, dashboard data, and exported fixtures.

### Evaluation

- Five-run demo success rate.
- Startup time, health-check time, and recovery time.
- End-to-end p50/p95 latency on the actual venue-equivalent setup.
- Consistency of metric claims across release report and presentation.
- Reviewer feedback on clarity of value, safety, and technical differentiation.

### Acceptance criteria

- Five consecutive full rehearsals succeed on the release candidate.
- One complete rehearsal succeeds with internet disconnected.
- The team can recover from each scripted failure within the allocated demo window.
- No unreviewed model/content/configuration change occurs after freeze.
- Every visible child-facing response has approved provenance; demo logs contain no raw media/PII.
- The final narrative demonstrates product value first, then measurable AI value, then reliability evidence.

### Risks

- Last-minute feature additions can invalidate evaluation and reliability. Mitigation: strict freeze; only P0 fixes after 27 October.
- Venue noise/network can break the primary path. Mitigation: device-recorded noisy evaluation, cache-first audio, local demo twin, and explicit offline switch.
- The demo may overemphasize architecture. Mitigation: begin with a child learning interaction and expose traces/metrics only as proof.

### Working-state checkpoint

The repository contains the exact release artifact, evaluation summary, demo fixtures, and recovery runbook used in five consecutive successful rehearsals.

## 11. Cross-phase quality gates

These gates apply to every merge, not only the phase where they are introduced:

| Gate | Required behavior |
|---|---|
| Repository health | Build, lint/type checks, migrations, and relevant tests pass |
| Backward compatibility | Existing simulator/demo path remains runnable |
| Contract safety | External schema changes are additive or explicitly versioned |
| State integrity | No provider callback can mutate state directly or bypass `state_version` |
| Child-error integrity | System uncertainty is never persisted as child incorrectness |
| Content provenance | Every normal response references approved curriculum/template content |
| Privacy | No raw child media or direct identifier in ordinary telemetry |
| Feature rollback | New provider/AI behavior has a bypass or feature flag until frozen |
| Observability | New critical path has trace spans, outcome codes, and latency metrics |
| Evidence | Every claim is tied to a versioned dataset, test, or rehearsal result |

## 12. Pull-request slicing strategy

Avoid one PR per phase. Each phase should be delivered as small vertical or enabling increments:

1. Contract/schema and fixtures.
2. Domain behavior with unit tests.
3. Persistence or provider adapter with integration tests.
4. API/orchestrator wiring behind a flag.
5. Telemetry and replay/evaluation coverage.
6. Feature activation only after the phase gate passes.

Recommended PR characteristics:

- one primary behavior change;
- backwards-compatible migrations using expand/migrate/contract where needed;
- no unrelated formatting or package reorganization;
- recorded test command and phase acceptance criterion in the PR description;
- rollback method stated for provider, contract, and database changes;
- merge to `main` only when the repository remains runnable.

## 13. Competition cut-line

If time becomes constrained, protect this order:

### Must ship

- Phase 0 contracts/foundation;
- Phase 1 deterministic vertical slice;
- Phase 2 ASR plus cached/managed speech output;
- Phase 3 real device and parent-progress integration for one complete module;
- Phase 4 frozen evidence and safety gates;
- Phase 6 offline/fallback path;
- Phase 7 rehearsed release.

### Ship only if the evidence gate passes

- bounded semantic resolver;
- constrained LLM paraphrasing;
- triggered CV activity;
- more than one polished module.

### Do not build before the competition

- runtime multi-agent orchestration;
- unrestricted chatbot behavior;
- separate microservices, Kafka, or Kubernetes;
- a second vector database when PostgreSQL/direct lookup is sufficient;
- learned BKT without adequate interaction data;
- continuous cloud video or emotion inference;
- custom ASR fine-tuning without ethically governed, representative data;
- full offline feature parity.

## 14. Definition of roadmap success

The roadmap succeeds when the team can demonstrate, with a single reproducible release, that:

1. TOKI completes an approved learning activity on real hardware.
2. Deterministic policy controls state, correctness, safety, and persistence.
3. AI handles speech and only measured ambiguity; every model can abstain.
4. Parent-visible evidence accurately reflects durable attempts.
5. The system exposes latency, provenance, fallback, and version evidence.
6. The same core activity remains safe and usable when the network or a model fails.

