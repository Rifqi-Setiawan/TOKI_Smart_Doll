# Provider Interfaces, Fakes, and Simulators

## 1. Overview & Architectural Isolation

In accordance with `AI-001`, `AI-002`, `AI-003`, and `ADR-004`, external and probabilistic components (ASR, TTS, semantic resolution, paraphrasing, computer vision) are strictly treated as **replaceable evidence and rendering adapters**.

Core Design Principles:
- **No SDK Leaks (`AI-001`):** Third-party SDK exceptions and vendor data structures are normalized within adapter boundaries into standard `ProviderError` hierarchies.
- **Typed Evidence Only (`AI-003`):** AI adapters return immutable contract models (`ASRResult`, `AssessmentResult`, `VisionObservation`, etc.). Adapters are forbidden by architecture from accessing the database, executing repositories, or issuing physical doll commands.
- **Deterministic Offline Twin (`ADR-014`):** For competition and continuous integration environments, deterministic fakes replace cloud providers.
- **Feature Flags & Budgets (`DEV-004`, `AI-006`):** Optional AI features (semantic resolution, LLM paraphrasing, vision) can be toggled on or off via environment variables without requiring schema changes or failing runtime boots.

---

## 2. Provider Interfaces & Contracts

### 2.1 ASR (`app/speech/interfaces.py`)
- **Protocol:** `ASRProvider.transcribe(audio_bytes, audio_spec, correlation, timeout_s) -> ASRResult`
- **Output:** `ASRResult` with `status: ASRStatus` (`SUCCESS`, `ABSTAIN`, `UNCERTAIN`, `ERROR`), normalized transcript, confidence, and latency.

### 2.2 TTS (`app/speech/interfaces.py`)
- **Protocol:** `TTSProvider.synthesize(text, audio_asset_id, timeout_s) -> TTSResult`
- **Output:** `TTSResult` with `source: TTSSource` (`CACHED`, `DYNAMIC`, `FALLBACK`), asset reference, duration, and latency.

### 2.3 Semantic Resolver (`app/understanding/interfaces.py`)
- **Protocol:** `SemanticResolver.resolve_intent(transcript, expected_answers, correlation, timeout_s) -> AssessmentResult`
- **Output:** `AssessmentResult` with `status: AssessmentStatus` (`CORRECT`, `INCORRECT`, `UNCERTAIN`, `ABSTAIN`). In accordance with `FR-009`, `UNCERTAIN` is never marked correct.

### 2.4 Paraphraser (`app/response/interfaces.py`)
- **Protocol:** `Paraphraser.paraphrase(baseline_text, pedagogical_act, timeout_s) -> str`
- **Constraint:** Output text is strictly bounded to a maximum of 25 spoken words (`AI-008`).

### 2.5 Computer Vision (`app/vision/interfaces.py`)
- **Protocol:** `VisionProvider.detect_objects(frame_bytes, allowed_vocabulary, correlation, timeout_s) -> VisionObservation`
- **Constraint:** Only labels in `allowed_vocabulary` are emitted; unrecognized objects map to `VisionStatus.UNKNOWN` (`AI-009`).

---

## 3. Deterministic Fakes Catalog

All fakes reside in their respective domain packages and support reproducible testing and failure injection via `.set_mode()`:

| Fake Adapter | Class | Supported Simulation Modes |
|---|---|---|
| ASR | `FakeASRProvider` | `success`, `abstain`, `timeout`, `malformed`, `error` |
| TTS | `FakeTTSProvider` | `success`, `cached_only`, `dynamic_only`, `timeout`, `error` |
| Semantic | `FakeSemanticResolver`| `success`, `abstain`, `uncertain`, `timeout`, `error` |
| Paraphraser | `FakeParaphraser` | `passthrough`, `paraphrase`, `timeout`, `error`, `oversized` |
| Vision | `FakeVisionProvider` | `success`, `unknown`, `abstain`, `timeout`, `error` |

---

## 4. Hardware & Client Simulators

### 4.1 Device Simulator (`simulators/device_simulator.py`)
Simulates the physical doll (ESP32) runtime:
- Generates versioned `DeviceEnvelope` structures for handshakes and audio streams.
- Enforces the 32KB max audio chunk size limit (`SEC-003`).
- Consumes and validates incoming server `DeviceCommand` and `DeviceAck` envelopes against frozen JSON Schema specifications.

### 4.2 Flutter Simulator (`simulators/flutter_simulator.py`)
Simulates the guardian mobile companion application:
- Consumes parent progress projections: `ChildProgressDTO`, `SessionSummaryDTO`, and `SkillProgressDTO`.
- Enforces non-clinical phrasing invariants (`SEC-010`), ensuring diagnostic terms are never accepted.
