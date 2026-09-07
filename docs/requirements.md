# Requirements — TOKI Backend & Conversational AI

**Status:** normative baseline  
**Terakhir diperbarui:** 6 September 2026

## 1. Cara membaca dokumen

Kata **MUST**, **SHOULD**, **MAY**, dan **MUST NOT** bersifat normatif.

- **MUST:** diperlukan untuk release kompetisi.
- **SHOULD:** dibuat setelah vertical slice MUST stabil dan hanya bila tidak mengancam jadwal/reliability.
- **MAY:** opsional/future work.
- **MUST NOT:** dilarang pada target kompetisi kecuali decision record baru menyertakan bukti, trade-off, owner, dan rollback.

Setiap perubahan kode harus menyebut ID requirement yang dipenuhi. Requirement yang belum memiliki test atau bukti harus dianggap belum selesai.

## 2. Functional requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| FR-001 | MUST | Sistem mengelola sesi melalui explicit finite-state machine. | Normal/exception states, legal events, guard, deadline, retry, durable event, dan fallback memiliki test. |
| FR-002 | MUST | Hanya orchestrator yang boleh mengubah authoritative session state. | Adapter/provider tidak memiliki repository mutation path; stale callback ditolak. |
| FR-003 | MUST | Session start memerlukan authenticated device dan active guardian consent. | Invalid/revoked consent menghasilkan typed rejection tanpa membuat active session. |
| FR-004 | MUST | Device protocol memiliki version, `message_id`, `session_id`, `turn_id`, monotonic `seq`, timestamp, dan ACK. | Duplicate/out-of-order/stale event tidak menimbulkan duplicate side effect. |
| FR-005 | MUST | Sistem mendukung reconnect dan resume dari last durable, acknowledged state. | Disconnect/reconnect test tidak mengulang mastery atau playback yang sudah ACK. |
| FR-006 | MUST | Curriculum hanya mengambil version berstatus approved. | Draft/revoked content tidak dapat dipilih pada child session. |
| FR-007 | MUST | Satu activity mendefinisikan module, skill, difficulty, prompt, expected reply, answer spec, hints, retry, dan review status. | Schema validation dan round-trip persistence test lulus. |
| FR-008 | MUST | Answer assessment menjalankan exact/synonym/normalized/phonetic rules lebih dulu. | Frozen fixtures menghasilkan expected assessment secara deterministik. |
| FR-009 | MUST | Low-confidence/abstain/no-speech tidak boleh menjadi `INCORRECT`. | Property/regression test membuktikan invariant untuk semua uncertain status. |
| FR-010 | MUST | Sistem memberi maksimal satu child-friendly retry sebelum hint/choice/imitation/demonstration fallback sesuai activity. | Setiap retry path berakhir pada bounded next state. |
| FR-011 | MUST | Response planner selalu menghasilkan template-backed `ResponsePlan`. | Semua pedagogical act memiliki approved text/audio fallback dan provenance. |
| FR-012 | MUST | Safety escalation dapat menginterupsi state aktif. | Required high-severity cases segera memilih immutable reviewed canned response. |
| FR-013 | MUST | Audio output memakai cache-first routing. | Cache hit tidak memanggil TTS; TTS failure memakai approved fallback. |
| FR-014 | MUST | Valid attempt menghasilkan atomic turn, attempt, optional mastery, session snapshot, domain event, dan outbox write. | Failure pada salah satu write me-roll back seluruh transaction. |
| FR-015 | MUST | Mastery update memakai transparent versioned rule dan explanation code. | Update dapat direproduksi dari prior state + evidence + policy version. |
| FR-016 | MUST | Parent API memberikan progress/session summary non-klinis. | Guardian hanya melihat child yang terhubung; response tidak memuat diagnosis. |
| FR-017 | MUST | Analytics projection dapat dibangun ulang dari domain event/outbox. | Rebuild test menghasilkan projection yang sama tanpa mengubah attempt. |
| FR-018 | SHOULD | Bounded semantic resolver menangani hanya unresolved eligible turn. | Output fixed schema; timeout/error menjadi `ABSTAIN`; feature dapat dimatikan. |
| FR-019 | SHOULD | Constrained paraphraser membuat variasi dari approved response plan. | Candidate gagal validation dibuang; template tetap sukses. |
| FR-020 | SHOULD | Camera snapshot hanya dipicu activity yang memerlukannya. | Tidak ada continuous stream; stale/unknown result tidak memblokir sesi. |
| FR-021 | SHOULD | Operator evidence view menampilkan path, provenance, safety, latency, fallback, dan mastery explanation. | Satu demo turn dapat ditelusuri tanpa menampilkan PII/raw media. |
| FR-022 | MUST | Guardian/operator memiliki stop action yang segera mengakhiri interaction dengan aman. | Stop dari setiap active state mencapai ending/completed tanpa provider dependency. |

## 3. AI and model requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| AI-001 | MUST | Semua provider dibungkus adapter internal yang vendor-neutral. | Provider SDK object/error tidak keluar dari module adapter. |
| AI-002 | MUST | Semua probabilistic result memakai typed contract, model/provider version, status, latency, dan `ABSTAIN`/error semantics. | Malformed/unknown enum ditolak sebelum policy. |
| AI-003 | MUST | AI output adalah evidence/candidate dan tidak langsung memengaruhi state, mastery, safety, atau device command. | Architecture test dan code review gate membuktikan dependency direction. |
| AI-004 | MUST | ASR dipilih melalui benchmark audio Indonesia child/device-like. | Scorecard membandingkan ≥2 kandidat atau menjelaskan keterbatasan secara eksplisit. |
| AI-005 | MUST | Provider confidence tidak dianggap ground truth. | Assessment menggabungkan expected context/rules dan memiliki uncertainty outcome. |
| AI-006 | MUST | Setiap model call memiliki deadline, size/token budget, normalized error, dan fallback. | Timeout/failure-injection tidak menggantung turn. |
| AI-007 | SHOULD | Semantic resolver hanya dipromosikan bila menambah ≥5 percentage-point absolute ambiguous-turn completion sebagai target awal, tanpa safety/latency regression. | Frozen A/B/ablation report dan promotion decision tersedia. |
| AI-008 | SHOULD | LLM paraphraser memakai temperature rendah, maksimal 25 spoken words, satu concept, paling banyak satu question, tanpa tool/web/memory. | 100% schema, provenance, language, length, dan safety gate pada frozen set. |
| AI-009 | SHOULD | Object detection memakai curated activity-specific vocabulary, freshness, confidence threshold, dan `UNKNOWN`. | Per-class metrics dan unknown false-positive limit disetujui sebelum enable. |
| AI-010 | MAY | Attention proxy hanya berupa neutral face-present/head-orientation signal yang temporally smoothed. | Tidak menyimpan emotion label, tidak memengaruhi mastery, dan dapat abstain. |
| AI-011 | MUST NOT | Runtime memakai autonomous multi-agent/LangGraph loop. | Tidak ada agent tool loop pada child critical path. |
| AI-012 | MUST NOT | Child-facing model melakukan free chat, web search, shell/tool use, DB access, atau direct device control. | Security/architecture tests dan configuration deny capability tersebut. |
| AI-013 | MUST NOT | Model dilatih otomatis dari live child interaction. | Tidak ada training/export pipeline dari production events tanpa separate approved research process. |

## 4. Data and persistence requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| DATA-001 | MUST | PostgreSQL menjadi authoritative store. | State setelah accepted transition bertahan restart/reconnect. |
| DATA-002 | MUST | Session menggunakan optimistic concurrency `state_version`. | Concurrent/stale update gagal tanpa partial mutation. |
| DATA-003 | MUST | Approved curriculum version immutable. | Perubahan content menghasilkan version baru dan audit reviewer. |
| DATA-004 | MUST | Attempt transaction bersifat atomic dan idempotent. | Replayed `message_id`/`turn_id` tidak membuat duplicate attempt/mastery. |
| DATA-005 | MUST | Domain events append-only dan outbox berada dalam transaction yang sama. | Crash/retry test tidak kehilangan atau menggandakan projection side effect. |
| DATA-006 | MUST | Raw audio/frame ephemeral secara default dan dihapus setelah bounded processing. | Storage/log scan tidak menemukan retained raw media pada normal profile. |
| DATA-007 | MUST | Sistem menyimpan version metadata untuk curriculum, model, prompt, policy, threshold, firmware, dan release. | Satu turn dapat direproduksi/ditelusuri ke version yang digunakan. |
| DATA-008 | MUST | Child identity pseudonymous dan age band dipilih daripada exact DOB bila cukup. | Normal analytics/log tidak berisi direct identifier. |
| DATA-009 | MUST | Research media retention memerlukan consent, isolated storage, access control, encryption, dan expiry terpisah. | Normal configuration tidak dapat mengaktifkannya tanpa explicit reviewed setup. |
| DATA-010 | MUST | Guardian dapat revoke consent; deletion/export behavior didefinisikan sebelum pilot. | Integration test menolak sesi baru setelah revocation. |
| DATA-011 | MUST NOT | Menambah ChromaDB/vector DB pada competition baseline. | Structured SQL/direct lookup tetap menjadi retrieval default. |
| DATA-012 | MAY | pgvector ditambahkan pada PostgreSQL setelah benchmark menunjukkan kebutuhan corpus. | Decision record memuat Recall@k/MRR dan end-to-end gain. |

## 5. API and contract requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| API-001 | MUST | Contract memakai Pydantic/JSON Schema dan field `schema_version`. | Generated schema disimpan/tested; unknown enum ditolak. |
| API-002 | MUST | Binary audio dipisahkan dari compact JSON control envelope. | Protocol test memvalidasi negotiated codec/rate/duration/size. |
| API-003 | MUST | REST/WebSocket memakai TLS di deployment non-local. | Plaintext external connection ditolak/redirect sesuai platform. |
| API-004 | MUST | Breaking contract change memakai new version; additive change tetap backward-compatible. | Contract compatibility test berjalan di CI. |
| API-005 | MUST | Error response bertipe dan tidak membocorkan stack, credential, provider payload, atau prompt. | Security snapshot tests lulus. |
| API-006 | MUST | Provider callback membawa `session_id`, `turn_id`, dan expected `state_version`. | Mismatch/stale callback dibuang dan diobservasi. |
| API-007 | MUST | `/health/live`, `/health/ready`, dan `/health/demo` memiliki semantics berbeda. | Optional-provider outage menghasilkan `DEGRADED`, bukan membuat readiness gagal bila core siap. |

## 6. Safety, privacy, and security requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| SEC-001 | MUST | Guardian API memakai authentication dan resource-level authorization. | Cross-guardian access tests selalu gagal. |
| SEC-002 | MUST | Device memakai unique credential/short-lived session token dan tidak menyimpan cloud provider secret. | Firmware/config inspection dan auth tests lulus. |
| SEC-003 | MUST | Input memiliki hard limit untuk audio duration, payload size, text/token, dan request rate. | Oversized/flood tests ditolak sebelum expensive processing. |
| SEC-004 | MUST | Message replay dicegah dengan idempotency, sequence, dan session expiry. | Replay test tidak menimbulkan side effect baru. |
| SEC-005 | MUST | Safety engine fail-closed dan high-severity response berasal dari reviewed immutable content. | `child-safety-300-v1` release gate lulus. |
| SEC-006 | MUST | Prompt injection, off-curriculum request, PII disclosure, sexual/violent/danger/abuse/distress case diuji dalam bahasa Indonesia dan ASR-corrupted variants. | Frozen safety suite dan expected action tersedia. |
| SEC-007 | MUST | Structured log meredaksi transcript sensitif, child identifier, secret, prompt, raw media, dan provider payload. | Automated log/privacy scan menghasilkan 0 finding kritis. |
| SEC-008 | MUST | Role minimum: `GUARDIAN`, `CONTENT_REVIEWER`, `OPERATOR`, `ADMIN`. | Authorization matrix memiliki tests. |
| SEC-009 | MUST | Sistem menyediakan physical/guardian stop dan safe end-session audio. | Stop tidak bergantung pada LLM/ASR/TTS dynamic. |
| SEC-010 | MUST NOT | Sistem membuat diagnosis, emotion ground truth, atau clinical efficacy claim. | UI/API/content/release claims review lulus. |

## 7. Reliability and performance requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| REL-001 | MUST | Setiap active state memiliki bounded exit. | Model/property tests tidak menemukan terminal hang. |
| REL-002 | MUST | Retry hanya untuk operasi idempotent dan dibatasi. | Tidak ada unbounded retry; retry count muncul di trace. |
| REL-003 | MUST | Semantic/paraphrase tidak di-retry pada input sama; template fallback langsung tersedia. | Provider failure test tetap mengirim response valid. |
| REL-004 | MUST | Circuit breaker external provider memiliki `CLOSED`, `OPEN`, `HALF_OPEN`. | Open circuit bypass provider dan terlihat di `/health/demo`. |
| REL-005 | MUST | Core activity dapat selesai ketika external LLM/CV mati. | Offline/degraded acceptance test lulus. |
| REL-006 | MUST | Local demo twin memakai aplikasi/container dan API contract yang sama. | Cloud-to-local profile smoke test lulus. |
| REL-007 | MUST | TTS common path cache-first dan demo assets dipreload. | Demo bisa berbicara ketika dynamic TTS unavailable. |
| REL-008 | MUST | Target awal endpoint-to-first-audio p95 ≤3 s pada venue-equivalent setup. | Release report mencantumkan measured p50/p95/p99; hasil tidak boleh direkayasa. |
| REL-009 | MUST | 200-turn replay tidak memiliki illegal transition, duplicate attempt, atau state divergence. | Frozen release run lulus 100%. |
| REL-010 | MUST | 30-minute soak tidak memiliki unrecovered disconnect atau unbounded resource growth. | Soak report dan resource graph tersedia. |
| REL-011 | MUST | Lima full demo rehearsal berturut-turut berhasil pada release candidate. | Run log menautkan digest/release manifest yang sama. |

## 8. Observability requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| OBS-001 | MUST | Satu root trace dibuat per turn. | Trace memuat stage critical path dan correlation ID. |
| OBS-002 | MUST | Trace merekam anonymized IDs, state before/after, content/version provenance, provider/model/policy version, outcome, fallback, dan latency. | Required attribute test lulus. |
| OBS-003 | MUST | Metrics minimal meliputi completion, retry/fallback, p50/p95/p99, assessment, safety, reliability, DB/outbox, cost, dan device health. | Release dashboard/scorecard dapat menghitung metrik dari versioned events. |
| OBS-004 | MUST | Telemetry export asynchronous dan tidak memblokir audio response. | Telemetry outage tidak menggagalkan turn. |
| OBS-005 | MUST | Learning outcome membedakan system uncertainty dari child performance. | Dashboard tidak menampilkan low-confidence ASR sebagai jawaban salah. |

## 9. Evaluation and release requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| EVAL-001 | MUST | Evaluation memakai frozen, versioned datasets dan release-under-test melalui contract yang sama. | Dataset registry dan release manifest tersedia. |
| EVAL-002 | MUST | Minimal dataset mencakup child/device-like ASR, intent/answer, curriculum transition, ≥300 safety cases, vision, 200-turn reliability, dan ≥30-minute soak. | Dataset schema/label/leakage checks lulus atau keterbatasan dilaporkan jelas. |
| EVAL-003 | MUST | Metric calculator diuji dengan hand-computable fixtures. | Unit tests membuktikan formula benar. |
| EVAL-004 | MUST | Human review digunakan untuk developmental appropriateness dan nuanced safety. | Reviewer rubric, disagreement, dan adjudication dicatat. |
| EVAL-005 | MUST | Optional AI dibandingkan melalui ablation dengan deterministic baseline. | Enabled/disabled scorecard memisahkan value dan cost. |
| EVAL-006 | MUST | Release manifest pin code/image, DB revision, firmware, curriculum, safety/mastery policy, provider/model/prompt/threshold, feature flags, dan golden-suite result. | Artifact dapat dihubungkan ke exact rehearsal build. |

## 10. Developer and repository requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| DEV-001 | MUST | Python target 3.12, FastAPI, Pydantic v2, PostgreSQL, SQLAlchemy async, dan Alembic; perubahan stack perlu decision record. | Lockfile dan container build reproducible. |
| DEV-002 | MUST | Satu PR berfokus pada satu behavior/enabler dan meninggalkan repository runnable. | CI lulus dan PR menyebut requirement + rollback. |
| DEV-003 | MUST | Migration backward-compatible memakai expand/migrate/contract bila relevan. | Upgrade test lulus; rollback/data plan terdokumentasi. |
| DEV-004 | MUST | Provider dan optional AI dilindungi feature flag sampai release freeze. | Feature dapat dibypass tanpa schema rollback. |
| DEV-005 | MUST | CI menjalankan lint, type check, unit, contract, migration, safety, dan regression yang sesuai. | Required checks mandatory sebelum merge. |
| DEV-006 | MUST | Secret tidak disimpan di code/repository/log. | Secret scan lulus. |

## 11. Competition cut-line

### MUST ship

- contracts dan repository foundation;
- satu deterministic end-to-end activity terlebih dahulu;
- ASR benchmark + cache/managed Indonesian speech output;
- real device + progress API integration;
- frozen evidence dan safety gates;
- local/offline fallback untuk core activity;
- rehearsed release dan recovery runbook.

### Ship hanya jika promotion gate lulus

- bounded semantic resolver;
- constrained LLM paraphrasing;
- triggered CV activity;
- module tambahan setelah satu module excellent stabil.

### DO NOT BUILD sebelum kompetisi

- runtime multi-agent/autonomous orchestration;
- unrestricted chatbot;
- default vector RAG/ChromaDB;
- fine-tuned IndoBERT sebelum baseline membuktikan kebutuhan;
- XTTS-v2 untuk Indonesian;
- continuous cloud audio/video;
- emotion recognition/diagnosis;
- BKT/DKT/RL/LLM mastery tanpa data memadai;
- automatic curriculum publication;
- microservices, Kafka, Kubernetes, atau service mesh;
- demo yang hanya hidup dengan internet/model API.

