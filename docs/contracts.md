# TOKI Versioned Domain and API Contracts

**Document status:** Normative boundary contracts baseline  
**Schema version:** `1.0`  
**Last updated:** 2026-09-07  
**Task ID:** TASK-003  
**Requirement IDs:** API-001, API-002, API-004, API-005, API-006, AI-002  
**Architecture / ADR References:** Boundary contracts; AI evidence-only; ADR-003, ADR-004  

---

## 1. Overview & Boundary Ownership

This document defines the frozen contract boundaries separating the backend orchestrator from external actors, physical hardware, Flutter clients, and AI/CV adapters.

| Boundary | Interfacing Actor / Component | Core Contracts | Schema File |
|---|---|---|---|
| **Device Control** | ESP32-S3 Firmware | `DeviceEnvelope`, `DeviceCommand`, `DeviceEvent`, `DeviceAck`, `AudioSpec` | `device_envelope.json`, `device_command.json`, `device_event.json` |
| **Speech Recognition** | ASR Adapters (Fake, Local, Managed) | `ASRResult`, `ASRStatus` | `asr_result.json` |
| **Audio Rendering** | TTS Adapters & Audio Cache | `TTSResult`, `TTSSource` | `tts_result.json` |
| **Answer Assessment** | Understanding Engine & Semantic Resolver | `AssessmentResult`, `AssessmentStatus`, `AssessmentReasonCode` | `assessment_result.json` |
| **Response Planning** | Pedagogical Response Planner & Paraphraser | `ResponsePlan`, `PedagogicalAct`, `ContentProvenance` | `response_plan.json` |
| **Computer Vision** | Triggered Camera Snapshot Adapter | `VisionObservation`, `VisionStatus`, `DetectedObject` | `vision_observation.json` |
| **Learning & Mastery** | Deterministic Mastery Engine & Outbox | `LearningEvidence`, `MasteryUpdate`, `MasteryBand` | `learning_evidence.json` |
| **Parent Progress** | Flutter Guardian Mobile App | `ChildProgressDTO`, `SessionSummaryDTO`, `SkillProgressDTO` | `child_progress_dto.json` |
| **Errors & Telemetry** | All External Clients | `ErrorResponse`, `ErrorCode` | `error_response.json` |

---

## 2. Invariants & Guarantees

### 2.1 Schema Versioning & Evolution (API-001, API-004)
- Every contract model inherits from `ContractModel` and contains `schema_version = "1.0"`.
- **Additive changes** (e.g. adding an optional field with default value) are backward-compatible and remain on the minor schema version.
- **Breaking changes** (e.g. removing a field, changing field types, modifying enum semantics) require a major version increment (`schema_version = "2.0"`) and an accepted ADR recorded in `docs/decisions.md`.

### 2.2 Media & Control Separation (API-002, SEC-003)
- Binary audio data is **never** embedded inside JSON envelopes.
- Control messages use compact JSON `DeviceEnvelope`.
- Binary audio chunks travel over dedicated WebSocket binary frames accompanied by `AudioMetadata` carrying monotonic `chunk_index` and `byte_length <= 32768`.

### 2.3 Mandatory Callback Correlation (API-006, ADR-003)
- Asynchronous adapters and external callbacks (ASR, TTS, CV, Semantic Resolver) inherit from `CallbackCorrelation`.
- Callbacks **must** supply `session_id`, `turn_id`, and `state_version >= 1`.
- Stale callbacks whose `state_version` does not match the orchestrator's active turn state are discarded with an observability log.

### 2.4 Bounded Probabilistic Evidence (AI-002, ADR-004)
- Probabilistic outputs carry explicit `status` (`SUCCESS`, `ABSTAIN`, `UNCERTAIN`, `TIMEOUT`, `ERROR`), latency in milliseconds, and model version.
- Adapters can return `ABSTAIN` or `UNCERTAIN` cleanly without raising unexpected exceptions.
- System uncertainty is never persisted as child error (FR-009).

### 2.5 Security & Redaction (API-005, ADR-013)
- `ErrorResponse` automatically sanitizes `details` by redacting keys containing `key`, `secret`, `password`, `token`, `prompt`, `traceback`, `payload`, or `credential`.
- Raw child media and direct PII are never present in error messages or logs.

### 2.6 Non-Clinical Copy Enforcement (SEC-010, FR-016)
- Progress contracts consumed by the Flutter guardian app validate that parent recommendations and tips do not contain clinical or diagnostic terms (`diagnosis`, `terapi`, `speech delay`, `gangguan`, `kelainan`, `abnormal`).
- TOKI is strictly bounded as an educational speech-stimulation companion, not a medical or diagnostic tool.

---

## 3. Fixture Catalog

Golden contract fixtures for testing and integration simulators are stored in `tests/fixtures/contracts/`:
- `device_envelope_valid.json` & `device_envelope_invalid.json`
- `asr_result_valid.json` & `asr_result_invalid.json`
- `assessment_result_valid.json` & `assessment_result_invalid.json`
- `response_plan_valid.json` & `response_plan_invalid.json`
- `vision_observation_valid.json`
- `child_progress_valid.json` & `child_progress_invalid.json`
- `error_response_valid.json`
