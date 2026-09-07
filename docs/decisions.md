# Architecture Decision Log — TOKI

**Status:** accepted baseline  
**Terakhir diperbarui:** 6 September 2026

## 1. Tujuan

Dokumen ini mencegah agent atau engineer menghidupkan kembali pilihan yang telah ditolak tanpa bukti baru. Proposal awal tetap menjadi konteks, tetapi keputusan di sini bersama requirement yang teruji adalah baseline implementasi.

## 2. Hierarki source of truth

Jika informasi bertentangan, gunakan urutan berikut:

1. aturan kompetisi resmi dan requirement legal/safety terbaru;
2. repository aktual, test, migration, dan versioned contract;
3. `requirements.md`;
4. accepted decision pada dokumen ini;
5. `problem.md`;
6. `README.md` dan implementation roadmap;
7. proposal awal, slide, atau asumsi percakapan.

Perbedaan antara repository dan dokumen tidak boleh diselesaikan diam-diam. Catat gap, perbarui dokumen/decision, dan sertakan test.

## 3. Status keputusan

- **ACCEPTED:** baseline yang harus diikuti.
- **PROPOSED:** belum boleh menjadi critical-path dependency.
- **DEFERRED:** dipertimbangkan setelah kompetisi atau setelah evidence gate.
- **REJECTED:** tidak boleh dibuat pada target ini tanpa decision baru.
- **SUPERSEDED:** digantikan decision yang lebih baru.

## 4. Decision summary

| ID | Status | Keputusan |
|---|---|---|
| ADR-001 | ACCEPTED | Produk adalah bounded educational companion, bukan chatbot/diagnostic tool. |
| ADR-002 | ACCEPTED | Backend memakai modular monolith. |
| ADR-003 | ACCEPTED | Runtime control memakai deterministic finite-state machine, tanpa agent. |
| ADR-004 | ACCEPTED | AI hanya evidence/candidate melalui typed adapters dan dapat abstain. |
| ADR-005 | ACCEPTED | Runtime curriculum retrieval memakai structured SQL/metadata, bukan default RAG. |
| ADR-006 | ACCEPTED | Answer understanding deterministic-first; semantic AI hanya untuk ambiguity. |
| ADR-007 | ACCEPTED | Response template-first; LLM paraphrasing opsional dan constrained. |
| ADR-008 | ACCEPTED | ASR/TTS provider dipilih melalui benchmark dan adapter. |
| ADR-009 | ACCEPTED | TTS cache-first; XTTS-v2 ditolak untuk Indonesian baseline. |
| ADR-010 | ACCEPTED | Vision dipicu activity dan vocabulary dibatasi; no continuous perception. |
| ADR-011 | ACCEPTED | Adaptasi awal memakai transparent rule-based mastery. |
| ADR-012 | ACCEPTED | PostgreSQL + transaction + append-only event/outbox menjadi data architecture. |
| ADR-013 | ACCEPTED | Raw child media ephemeral by default. |
| ADR-014 | ACCEPTED | Cloud primary memiliki local demo twin dengan kontrak sama. |
| ADR-015 | ACCEPTED | Reliability/evaluation adalah release gate, bukan pekerjaan akhir. |
| ADR-016 | ACCEPTED | Optional AI hanya aktif setelah measurable promotion gate. |

## ADR-001 — Bounded educational companion

**Context:** Pengguna berusia 3–6 tahun; open-domain AI memiliki risiko konten, privasi, klaim medis, dan unpredictability.

**Decision:** TOKI menyajikan aktivitas kurikulum yang disetujui dan adult-mediated. Sistem tidak membuat diagnosis, terapi, clinical score, emotion ground truth, atau unrestricted conversation.

**Consequences:** Ruang percakapan lebih sempit, tetapi safety, evaluasi, provenance, dan demo menjadi defensible. Semua UI/API copy harus memakai bahasa non-klinis.

## ADR-002 — Modular monolith

**Context:** Waktu sekitar 12 minggu, tim kecil, critical flow pendek, dan demo membutuhkan deployment sederhana.

**Decision:** Semua business modules hidup dalam satu FastAPI application/container dengan internal interface yang jelas. PostgreSQL menjadi store bersama. Sidecar lokal hanya boleh untuk GPU inference bila benar-benar perlu.

**Rejected:** microservices, Kafka, Kubernetes, service mesh.

**Why:** Mengurangi network hop, deployment, distributed state, observability overhead, dan failure point.

**Trade-off:** Independent scaling lebih terbatas. Ini dapat ditinjau ulang setelah profiling production, bukan berdasarkan kemungkinan hipotetis.

## ADR-003 — Deterministic finite-state machine, no runtime agent

**Context:** Proposal mengarah ke agentic orchestration, tetapi setiap runtime step mempunyai input, output, tool, dan next state yang dapat didefinisikan.

**Decision:** Session orchestrator mengontrol explicit states, events, guards, deadlines, retries, durable transition, dan fallback. Hanya orchestrator boleh mengubah state.

**Rejected:** LangGraph/autonomous multi-agent/CG-ARAG pada child interaction path.

**Why:** Agent tidak dibutuhkan untuk planning terbuka; autonomy justru menaikkan latency, nondeterminism, debugging, dan safety risk.

**Invariant:** Provider callback membawa `session_id`, `turn_id`, `state_version`; stale result dibuang.

## ADR-004 — AI is bounded evidence, not policy

**Context:** ASR, semantics, CV, dan generation bersifat probabilistik.

**Decision:** Semua AI diakses melalui vendor-neutral adapter dan menghasilkan typed evidence/candidate. Deterministic code memvalidasi dan mengambil final policy decision. Setiap component memiliki `ABSTAIN`, timeout, budget, feature flag, dan fallback.

**Rejected:** model yang langsung memilih aktivitas, menulis mastery, mengubah state, mengakses DB/web/tools, atau memberi device command.

**Trade-off:** Lebih banyak contract dan validator, tetapi failure dapat dilokalisasi dan diaudit.

## ADR-005 — Structured curriculum retrieval first

**Context:** Lima module awal kecil, structured, safety-reviewed, dan perlu exact provenance.

**Decision:** Gunakan PostgreSQL filtering/ranking berdasarkan module, skill, level, recent exposure, mastery band, dan optional object context.

**Rejected:** LangChain + ChromaDB + hybrid RAG sebagai default child runtime.

**Why:** Direct lookup lebih cepat, predictable, murah, dan memiliki exact provenance.

**Revisit condition:** Corpus berkembang signifikan dan pgvector/full-text benchmark menunjukkan peningkatan Recall@k/MRR serta end-to-end correctness. Jika perlu, gunakan pgvector di PostgreSQL terlebih dahulu.

## ADR-006 — Deterministic-first answer understanding

**Context:** Intent set dan domain activity kecil, sementara child speech noisy.

**Decision:** Jalankan normalization, expected phrase, synonym, phonetic, dan contextual rules lebih dulu. Bounded semantic resolver hanya menerima unresolved eligible turn dan mengembalikan fixed decision schema atau `ABSTAIN`.

**Rejected:** fine-tuned IndoBERT sebagai baseline awal.

**Why:** Tidak ada bukti dataset cukup untuk fine-tuning; rules memberikan baseline cepat dan interpretable.

**Invariant:** Low understanding confidence tidak boleh disimpan sebagai `INCORRECT`.

## ADR-007 — Template-first responses

**Context:** Free-form LLM dapat menghasilkan respons panjang, off-curriculum, atau tidak aman.

**Decision:** Deterministic response planner selalu menyiapkan approved template, audio fallback, gesture enum, dan provenance. LLM paraphraser, jika enabled, hanya merender plan itu menjadi maksimal 25 spoken words dan hasilnya divalidasi.

**Rejected:** unrestricted LLM chat dan generation tanpa fallback/provenance.

**Failure behavior:** Invalid, unsafe, stale, atau slow candidate dibuang; template dipakai tanpa retry LLM.

## ADR-008 — Benchmark-selected speech adapters

**Context:** Young-child Indonesian speech adalah uncertainty teknis terbesar; reputasi model dewasa tidak cukup.

**Decision:** Definisikan common ASR/TTS interface. Pilih primary/backup berdasarkan device-like dataset, expected-concept accuracy, WER/CER, abstention behavior, latency p50/p95, intelligibility, privacy, dan cost.

**Candidate, not locked:** managed Indonesian streaming ASR dan faster-whisper local fallback hanya setelah benchmark pada exact demo laptop.

**Consequence:** Vendor/model belum final sampai scorecard tersedia. Semua release harus pin version.

## ADR-009 — Cache-first supported Indonesian TTS

**Context:** Common prompt bersifat tetap dan dynamic TTS menambah latency/outage risk. XTTS-v2 tidak memiliki official Indonesian support pada investigasi.

**Decision:** Pre-generate/cache seluruh common prompt dan fallback. Dynamic TTS memakai voice `id-ID` yang didukung dan hanya pada cache miss.

**Rejected:** XTTS-v2 sebagai dependency Indonesian competition path.

**Fallback:** exact cached asset → managed TTS untuk approved template → generic cached safe asset → safe stop.

## ADR-010 — Triggered, bounded vision

**Context:** Continuous/open-vocabulary vision membebani ESP32-S3, privasi, latency, dan calibration.

**Decision:** Camera hanya mengirim snapshot setelah `CAPTURE_OBJECT` untuk activity aktif. Detector memakai curated allowed vocabulary, threshold, freshness window, dan typed `UNKNOWN/ABSTAIN/ERROR`.

**Rejected:** always-on video, face recognition, speaker identification, dan emotion recognition.

**Invariant:** CV tidak memengaruhi mastery secara langsung dan kegagalannya tidak boleh memblokir base speech activity.

## ADR-011 — Rule-based mastery first

**Context:** BKT/DKT memerlukan skill tags, interaction history, parameter estimation, dan data berkualitas yang belum tersedia.

**Decision:** Gunakan transparent versioned rules dari eligible learning evidence, lengkap dengan previous/new score, band, next action, dan explanation codes.

**Deferred:** constrained BKT setelah jumlah history dan validasi ahli mencukupi.

**Rejected:** DKT, reinforcement learning, atau LLM-estimated mastery untuk competition release.

## ADR-012 — PostgreSQL, atomic transaction, event/outbox

**Context:** Session state, curriculum, mastery, analytics, dan audit perlu konsistensi dan reproducibility; scale kompetisi tidak membenarkan banyak data system.

**Decision:** PostgreSQL menyimpan identity/consent, immutable curriculum versions, runtime state, attempt, mastery, AI metadata, domain events, outbox, dan read projections.

Satu resolved attempt menulis secara atomik:

1. turn resolution;
2. attempt/learning evidence;
3. mastery state/history bila eligible;
4. next session snapshot;
5. append-only domain event;
6. outbox event.

**Rejected:** multiple operational databases dan external event platform pada baseline.

## ADR-013 — Child-data minimization

**Context:** Audio/video dan identitas anak adalah data sensitif dan tidak perlu disimpan untuk normal learning loop.

**Decision:** Raw audio/frame bersifat transient dan dihapus setelah processing. Normal logs menyimpan pseudonymous ID, reason code, durations, versions, dan redacted features. Research retention membutuhkan separate consent, isolated encrypted storage, RBAC, expiry, dan approval.

**Consequence:** Error analysis dari raw media harus dilakukan hanya dalam governed evaluation environment; normal telemetry lebih terbatas tetapi jauh lebih aman.

## ADR-014 — Cloud primary plus local demo twin

**Context:** Cloud provider memberi kualitas speech/model baik, tetapi venue internet, quota, atau provider dapat gagal.

**Decision:** Primary deployment memakai satu warm cloud container + managed PostgreSQL. Backup memakai aplikasi/container dan API contract sama pada laptop/hotspot, local PostgreSQL/seed, cached curriculum/audio, deterministic assessment, dan optional validated local models.

**Rejected:** cloud-only demo dan full offline feature parity.

**Scope local:** minimal satu complete strong activity per module; optional AI boleh disabled.

## ADR-015 — Evidence and reliability as release gates

**Context:** Demo ad hoc tidak membuktikan safety, correctness, atau reliability.

**Decision:** Release candidate harus terkait frozen datasets, deterministic metrics, human review bila perlu, 300-case safety suite, 200-turn replay, 30-minute soak, failure injection, latency report, dan five consecutive rehearsals.

**Consequence:** Feature yang belum diukur tidak masuk final path walaupun terlihat menarik.

## ADR-016 — Optional AI promotion gate

**Context:** Semantic resolver/paraphraser dapat menambah naturalness tetapi juga latency, cost, dan risk.

**Decision:** Optional AI tetap di balik independent feature flag. Promotion awal memerlukan peningkatan absolut sekitar ≥5 percentage points pada ambiguous-turn completion, zero high-severity safety regression, 100% valid schema/provenance, dan measured p95 tetap pada budget target. Effect threshold boleh dikalibrasi jika confidence interval dataset membuat angka tersebut tidak defensible.

**Failure/reversal:** Disable feature flag tanpa schema rollback. Negative result sah dan harus dilaporkan, bukan ditutupi.

## 5. Keputusan yang belum final

| Topic | Status | Owner/evidence yang diperlukan |
|---|---|---|
| Exact ASR provider/model | PROPOSED | backend; child/device-like benchmark |
| Exact managed TTS/voice | PROPOSED | backend + curriculum reviewer; pronunciation/intelligibility test |
| Semantic/LLM model | PROPOSED | backend; frozen ablation dan safety/latency gate |
| CV model/labels/threshold | PROPOSED | CV team; per-class device-camera evaluation |
| Mastery formula/threshold | PROPOSED | backend + curriculum/psychology reviewer |
| Exact retention period | PROPOSED | product/privacy owner sebelum pilot |
| Cloud region/instance sizing | PROPOSED | backend/DevOps; load and venue test |
| Attention proxy | DEFERRED | CV + expert review; construct validity evidence |
| pgvector/RAG | DEFERRED | retrieval benchmark setelah corpus need |
| BKT | DEFERRED | sufficient governed history + calibration |

## 6. Cara mengubah keputusan

Jangan mengedit keputusan lama agar seolah-olah tidak pernah ada. Tambahkan ADR baru dengan:

```markdown
## ADR-NNN — Judul

Status: PROPOSED | ACCEPTED | REJECTED | SUPERSEDED
Date:
Owner:
Supersedes:

### Context
Masalah, constraint, dan bukti baru.

### Options
Minimal selected option dan credible alternative.

### Decision
Pilihan dan scope tepat.

### Why
Accuracy/effectiveness, implementation time, reliability, cost, latency,
maintainability, demo risk, differentiation.

### Consequences
Benefit, trade-off, migration, security/privacy, observability.

### Acceptance and evidence
Metric, dataset, test, threshold, owner.

### Rollback/revisit trigger
Cara kembali dan kondisi evaluasi ulang.
```

Major architecture change belum dianggap accepted sampai requirement, test/evaluation, migration, dan rollback-nya jelas.

## 7. Guardrail untuk agent AI

Agent wajib berhenti dan membuat proposal ADR—bukan langsung mengimplementasikan—jika ingin:

- menambah service/database/message broker;
- menambah autonomous agent atau tool-using model;
- memberi AI hak mengubah state/mastery/safety/device;
- menyimpan raw child media;
- mengubah product claim menjadi diagnostic/therapeutic;
- menambah RAG/vector database;
- mengganti contract secara breaking;
- menghapus local demo fallback;
- mengaktifkan optional AI tanpa frozen comparison.

Agent boleh langsung membuat perubahan kecil yang sesuai keputusan, reversible, teruji, dan menjaga repository runnable.

