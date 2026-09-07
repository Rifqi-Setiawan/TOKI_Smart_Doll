# TOKI — Backend & Conversational AI

> Dokumentasi eksekusi untuk agent AI dan engineer yang mengembangkan TOKI pada LIDM 2026, divisi Inovasi Teknologi Digital Pendidikan (ITDP).

**Status dokumen:** baseline implementasi yang disetujui  
**Terakhir diperbarui:** 6 September 2026  
**Target demo final:** 2–4 November 2026  
**Pemilik utama subsystem:** Backend & Conversational AI Developer

## Ringkasan proyek

TOKI adalah pendamping belajar berbentuk panda berbasis AI/IoT untuk anak Indonesia usia kurang lebih 3–6 tahun di bawah pendampingan orang dewasa. Sistem memberikan aktivitas stimulasi berbicara yang singkat, menyenangkan, dan telah disetujui ahli; memahami upaya anak secara hati-hati; memberikan respons yang sesuai; memperbarui bukti perkembangan; dan menyajikan ringkasan yang mudah dipahami kepada orang tua.

TOKI **bukan** chatbot umum, terapis, alat diagnosis speech delay, atau pengganti orang tua/guru. Klaim produk dibatasi pada pendamping belajar dan stimulasi berbicara.

Unit keberhasilan utama bukan “jawaban AI yang terdengar pintar”, melainkan satu learning turn yang selesai dengan aman:

```text
prompt → upaya anak → interpretasi → feedback → bukti skill → langkah berikutnya
```

## Keputusan arsitektur inti

- Backend berbentuk **modular monolith** dalam satu aplikasi FastAPI dan satu image/container.
- **Finite-state machine deterministik** mengontrol sesi, aktivitas, retry, safety, persistence, mastery, dan fallback.
- AI hanya menjadi evidence atau renderer: ASR, resolver semantik terbatas, paraphraser opsional, TTS, dan object detection terpicu.
- AI tidak boleh langsung mengubah state, menentukan kurikulum, menulis mastery, menjalankan tools, mengakses web, atau mengendalikan perangkat.
- Semua output AI memakai kontrak terstruktur, deadline, validasi deterministik, kemampuan `ABSTAIN`, dan fallback.
- Konten berasal dari kurikulum terstruktur, versioned, immutable setelah disetujui, dan memiliki provenance.
- PostgreSQL menjadi source of truth untuk state, attempt, mastery, domain event, outbox, dan analytics projection.
- Audio/video anak bersifat ephemeral secara default; log tidak boleh menyimpan raw child media atau direct identifier.
- Deployment utama di cloud dan tersedia **local demo twin** untuk menyelesaikan minimal satu aktivitas penuh saat internet/model gagal.
- Tidak ada runtime multi-agent, LangGraph agent loop, unrestricted RAG, ChromaDB, atau microservices sebelum kompetisi.

Dokumentasi kanonis tersedia di [problem](./docs/problem.md), [requirements](./docs/requirements.md), [architecture](./docs/architecture.md), [architecture decisions/ADR](./docs/decisions.md), [roadmap](./docs/roadmap.md), dan [evaluation](./docs/evaluation.md).

## Scope subsystem

### Dimiliki Backend & Conversational AI

- REST API dan WebSocket protocol;
- device authentication, sequence, ACK, deduplication, reconnect, dan resume;
- session orchestrator dan state machine;
- schema, migration, repository, transaction, domain event, dan outbox;
- ASR adapter dan normalized result;
- deterministic answer assessment dan bounded semantic resolver;
- response planning, safety validation, audio cache, TTS adapter, dan fallback;
- rule-based mastery berdasarkan attempt yang valid;
- parent progress API dan analytics projection contract;
- telemetry, redaction, health check, replay, dan evaluation hooks.

### Interface lintas tim

- **Hardware:** codec/sample rate, audio chunks, VAD/end event, command/ACK, camera snapshot, gesture/display enum.
- **Curriculum/psychology:** module, skill, activity, answer spec, hint ladder, approved responses, safety wording, review status.
- **Computer vision:** snapshot request dan `VisionObservation`; CV tidak pernah langsung memengaruhi mastery.
- **Flutter:** guardian auth/consent, profile, session summary, progress DTO, dan local/cloud base URL.
- **DevOps/demo:** cloud deployment, local profile, release manifest, secrets, preflight, dan recovery runbook.

## Target struktur repository

### Struktur yang tersedia saat ini

Repository saat ini berisi dokumentasi dan berkas orkestrasi agent berikut. Source code aplikasi, konfigurasi runtime, deployment, dan artefak evaluasi belum tersedia sebagai berkas yang dapat dijalankan.

```text
.
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── evaluation.md
│   ├── problem.md
│   ├── requirements.md
│   └── roadmap.md
├── tasks/
│   ├── index.md
│   ├── TASK-001.md
│   ├── TASK-002.md
│   └── ...
├── handoffs/
│   ├── latest.md
│   └── history/
├── AGENTS.md
├── CURRENT_TASK.md
└── README.md
```

### Struktur target implementasi

Struktur berikut adalah target Phase 0, bukan deskripsi fitur yang sudah tersedia. Agent boleh menambahkan submodule di dalam boundary yang disetujui. Perubahan arsitektur mayor harus didokumentasikan sebagai ADR di `docs/decisions.md`, mengikuti lifecycle yang sudah ditetapkan di sana, dan tidak boleh diimplementasikan secara diam-diam.

```text
.
├── app/
│   ├── api/                 # REST, WebSocket, health endpoints
│   ├── device_protocol/     # envelope, seq, ACK, resume
│   ├── sessions/            # orchestrator, state, transition
│   ├── curriculum/          # approved content dan activity rules
│   ├── understanding/       # ASR normalization dan assessment
│   ├── response/            # plan, templates, validators
│   ├── safety/              # policy dan canned escalation
│   ├── speech/              # ASR/TTS adapters dan audio cache
│   ├── vision/              # triggered CV adapter
│   ├── mastery/             # rule-based learning evidence
│   ├── analytics/           # parent-safe projections
│   ├── persistence/         # repositories, transactions, outbox
│   ├── telemetry/           # traces, metrics, redaction
│   ├── evaluation/          # replay dan scorers
│   └── config/              # settings, budgets, feature flags
├── migrations/
├── curriculum/
├── evaluation/
│   ├── datasets/
│   ├── fixtures/
│   └── reports/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── regression/
│   └── failure_injection/
├── demo/
├── deploy/
├── scripts/
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── evaluation.md
│   ├── problem.md
│   ├── requirements.md
│   └── roadmap.md
├── tasks/
│   ├── index.md
│   ├── TASK-001.md
│   ├── TASK-002.md
│   └── ...
├── handoffs/
│   ├── latest.md
│   └── history/
├── AGENTS.md
├── CURRENT_TASK.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Cara menjalankan

### Status saat dokumentasi dibuat

Workspace belum berisi source code, `pyproject.toml`, Dockerfile, Compose file, migration, maupun `.env.example`. Karena itu, proyek **belum dapat dijalankan saat ini**. Perintah di bawah adalah interface operasional yang wajib diwujudkan pada Phase 0; agent tidak boleh mengklaim perintah berhasil sebelum file tersebut benar-benar tersedia dan diuji.

### Prasyarat target

- Git;
- Docker Engine 24+ dan Docker Compose v2;
- untuk mode native: Python 3.12 dan `uv`;
- perangkat ESP32-S3 atau device simulator;
- credential provider hanya jika fitur provider tersebut diaktifkan.

### Quick start target — Docker

```bash
git clone <repository-url>
cd <repository-directory>
cp .env.example .env
docker compose up --build -d postgres
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m scripts.seed_demo
docker compose up --build api
```

Verifikasi:

```bash
curl --fail http://localhost:8000/health/live
curl --fail http://localhost:8000/health/ready
curl --fail http://localhost:8000/health/demo
```

Dokumentasi API target tersedia di `http://localhost:8000/docs` pada environment development.

### Quick start target — native development

```bash
cp .env.example .env
uv sync --all-groups
uv run alembic upgrade head
uv run python -m scripts.seed_demo
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

PostgreSQL tetap harus tersedia, misalnya melalui:

```bash
docker compose up -d postgres
```

### Menjalankan baseline tanpa provider eksternal

Mode ini wajib menjadi jalur pertama yang hidup. Semua adapter memakai fake/local deterministic implementation dan semua audio demo berasal dari cache.

```bash
TOKI_PROFILE=test \
TOKI_ASR_PROVIDER=fake \
TOKI_SEMANTIC_ENABLED=false \
TOKI_LLM_PARAPHRASE_ENABLED=false \
TOKI_TTS_PROVIDER=cached \
TOKI_VISION_ENABLED=false \
uv run uvicorn app.main:app --port 8000
```

Lalu jalankan replay smoke test:

```bash
uv run python -m app.evaluation.replay evaluation/fixtures/smoke.jsonl
```

### Menjalankan test dan quality gate

Nama command berikut menjadi kontrak developer experience Phase 0:

```bash
uv run ruff check .
uv run mypy app
uv run pytest tests/unit tests/contract
uv run pytest tests/integration
uv run pytest tests/regression
```

Release candidate juga wajib menjalankan:

```bash
uv run pytest tests/failure_injection
uv run python -m app.evaluation.replay evaluation/datasets/reliability-replay-200-v1.jsonl
uv run python -m scripts.demo_healthcheck
```

### Konfigurasi environment target

`.env.example` harus mendokumentasikan sekurang-kurangnya:

```dotenv
TOKI_ENV=development
TOKI_PROFILE=local
TOKI_LOG_LEVEL=INFO
TOKI_DATABASE_URL=postgresql+asyncpg://toki:toki@localhost:5432/toki

TOKI_ASR_PROVIDER=fake
TOKI_ASR_MODEL=pinned-model
TOKI_ASR_DEADLINE_MS=1200

TOKI_SEMANTIC_ENABLED=false
TOKI_SEMANTIC_MODEL=pinned-model
TOKI_LLM_PARAPHRASE_ENABLED=false
TOKI_LLM_MODEL=pinned-model

TOKI_TTS_PROVIDER=cached
TOKI_TTS_VOICE=pinned-id-ID
TOKI_VISION_ENABLED=false

TOKI_CURRICULUM_VERSION=dev
TOKI_SAFETY_POLICY_VERSION=CHILD-SAFETY-1.0
TOKI_MASTERY_POLICY_VERSION=RULE-MASTERY-1.0
TOKI_RAW_MEDIA_RETENTION=false
```

Nama key dapat diperluas, tetapi agent harus menjaga kompatibilitas dan tidak menaruh secret asli di repository.

## Endpoint minimum

| Interface | Tujuan |
|---|---|
| `GET /health/live` | proses hidup |
| `GET /health/ready` | DB dan approved curriculum siap |
| `GET /health/demo` | status device, cache, provider, circuit, dan release |
| `WS /v1/device/sessions/{session_id}` | binary audio dan typed device events |
| `POST /v1/sessions` | memulai sesi setelah auth dan consent check |
| `POST /v1/sessions/{id}/stop` | guardian/operator stop |
| `GET /v1/children/{id}/progress` | projection perkembangan non-klinis |
| `GET /v1/sessions/{id}/summary` | ringkasan sesi untuk guardian |

Path dapat berubah hanya melalui contract versioning dan ADR yang mengikuti lifecycle di `docs/decisions.md`; perubahan arsitektur mayor tidak boleh diimplementasikan secara diam-diam.

## Definition of done untuk setiap perubahan

Perubahan dianggap selesai hanya jika:

1. requirement/acceptance criterion yang dituju disebutkan;
2. lint, type check, migration, dan test relevan lulus;
3. perubahan contract backward-compatible atau versioned;
4. tidak ada provider callback yang langsung mengubah state;
5. uncertainty sistem tidak dicatat sebagai kesalahan anak;
6. child-facing output memiliki approved provenance atau canned fallback;
7. telemetry tidak membocorkan raw media, PII, prompt, atau secret;
8. failure path dan rollback/feature flag tersedia untuk komponen probabilistik;
9. repository tetap runnable pada akhir setiap PR;
10. klaim hasil didukung dataset, trace, test, atau rehearsal yang versioned.

## Urutan implementasi

1. **Foundation:** package, settings, contracts, DB/migration, fake adapters, CI.
2. **Deterministic vertical slice:** satu activity end-to-end tanpa external AI.
3. **Speech baseline:** ASR adapter benchmark, audio cache, supported Indonesian TTS.
4. **Integration:** ESP32 protocol, Flutter progress API, lima module melalui schema yang sama.
5. **Evaluation:** frozen fixtures, safety suite, replay, baseline scorecard.
6. **Bounded AI:** hanya aktif jika melewati promotion gate terhadap baseline.
7. **Reliability:** timeout, circuit breaker, offline activity pack, reconnect, failure injection.
8. **Demo freeze:** pinned release, five-run rehearsal, cloud/local switchover.

## Aturan kerja untuk agent AI

Mulai dengan urutan baca berikut:

1. [`AGENTS.md`](./AGENTS.md)
2. [`CURRENT_TASK.md`](./CURRENT_TASK.md)
3. [`handoffs/latest.md`](./handoffs/latest.md)
4. [`tasks/index.md`](./tasks/index.md)
5. active `tasks/TASK-XXX.md` yang ditunjuk oleh `CURRENT_TASK.md`

Untuk pekerjaan yang sensitif terhadap arsitektur, baca juga:

- [`docs/problem.md`](./docs/problem.md)
- [`docs/requirements.md`](./docs/requirements.md)
- [`docs/architecture.md`](./docs/architecture.md)
- [`docs/decisions.md`](./docs/decisions.md)

Ikuti aturan kerja lengkap di `AGENTS.md`; README ini hanya menyediakan urutan baca dan pointer ringkas.

- Periksa repository aktual; repository adalah source of truth untuk apa yang sudah terimplementasi.
- Jangan menganggap proposal sebagai spesifikasi final.
- Jangan memperluas scope dari satu modular monolith atau menambah agent/RAG/vector DB tanpa benchmark dan ADR yang diterima sesuai `docs/decisions.md`.
- Mulai dari satu perubahan kecil yang meninggalkan repository dalam kondisi berjalan.
- Jika requirement ambigu, buat asumsi eksplisit dan pilih solusi paling sederhana yang reversible.
- Jangan menulis “production-ready”, “aman 100%”, atau “offline-ready” tanpa bukti gate yang sesuai.
