# TOKI Repository Map and Boundary Inventory

**Document status:** Normative inventory baseline  
**Generated at:** 2026-09-07T10:14:00+07:00 (UTC+7)  
**Author / Agent:** Antigravity (Phase 0 — Foundation)  
**Task ID:** TASK-001  
**Requirement IDs:** DEV-001, DEV-002  
**Architecture / ADR References:** Modular monolith; ADR-002; Source-of-truth hierarchy  

---

## 1. Executive Summary

This document establishes the verified, evidence-based inventory of the `TOKI_Smart_Doll` repository as of starting commit `a8e019df526ffde379f9692cf585c480370c6065`.

Prior to this task, architectural and roadmap documentation had been authored without direct inspection of the physical repository tree. This inventory confirms the actual filesystem state, toolchains, entry points, and module boundaries so that subsequent engineering tasks (TASK-002 onwards) build directly on confirmed conventions without guesswork or redundant restructurings.

### Key Findings
1. **Repository Lifecycle State:** The repository is at **Day 0 / Phase 0**. It currently contains governance and planning documents (`docs/`, `tasks/`, `handoffs/`, `AGENTS.md`, `CURRENT_TASK.md`, `README.md`).
2. **Code & Runtime State:** No Python source code, package manifests (`pyproject.toml`), container definitions (`Dockerfile`, `docker-compose.yml`), migrations, or test implementations exist yet.
3. **Canonical Architecture Decision Log:** Verified that `docs/decisions.md` is the sole canonical architecture decision log. No parallel or conflicting ADR directories exist.
4. **Package Root Convention:** While empty `src/` and `evals/` directories were found on disk (untracked by git), all specification documents (`README.md`, `docs/architecture.md`, `docs/roadmap.md`) and all 28 task files uniformly specify `app/` as the application root and `evaluation/` as the evaluation root. `app/` is confirmed as the canonical application package name.
5. **Local Runtime Discrepancies:** The developer environment possesses `Python 3.13.14` and `pip 26.1.2`, but lacks `uv` and `docker` in `PATH`. Setup for TASK-002 must account for native Python execution options alongside containerized target paths.

---

## 2. Git & Version Control State

| Property | Value | Evidence / Command |
|---|---|---|
| **Repository URL** | `https://github.com/Rifqi-Setiawan/TOKI_Smart_Doll.git` | `git remote -v` |
| **Current Branch** | `main` | `git branch -v` (`* main a8e019d fix readme`) |
| **Upstream Status** | Up to date with `origin/main` | `git status` |
| **Starting Commit** | `a8e019df526ffde379f9692cf585c480370c6065` | `git log -1 --stat` |
| **Commit History** | 3 commits (`8e28b2f` → `c46ec34` → `a8e019d`) | `git log -n 5 --oneline` |
| **Working Tree Status** | Clean at task initiation | `git status` (no uncommitted tracked/untracked files) |
| **Tracked Files Count**| 42 tracked files | `git ls-files` |

### Tracked Files Breakdown
- Governance & Task Coordination (33 files): `AGENTS.md`, `CURRENT_TASK.md`, `tasks/index.md`, `tasks/backlog.md`, `tasks/TASK_TEMPLATE.md`, `tasks/TASK-001.md` through `tasks/TASK-028.md`.
- Handoff Documentation (2 files): `handoffs/latest.md`, `handoffs/history/README.md`.
- Core Documentation (6 files): `docs/problem.md`, `docs/requirements.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/roadmap.md`, `docs/evaluation.md`.
- Project Overview (1 file): `README.md`.

---

## 3. Environment & Runtime Inventory

Inspection performed on the host operating system:

| Tool / Runtime | Target in Docs (DEV-001) | Actual Host Status | Exit Code / Output | Notes |
|---|---|---|---|---|
| **OS** | Linux / Container / Windows | Windows 11 (PowerShell 5.1 / 7) | N/A | Windows execution host |
| **Python** | 3.12 (Pinned) | `Python 3.13.14` (64-bit) | 0 (`python --version`) | Python 3.13 installed globally |
| **Package Manager** | `uv` (recommended) | Not installed in `PATH` | CommandNotFoundException | Must install `uv` or use `python -m pip / venv` |
| **Containers** | Docker 24+, Compose v2 | Not installed in `PATH` | CommandNotFoundException | Docker daemon unavailable locally |
| **Git** | Git 2.x+ | `git version 2.55.0.windows.2` | 0 (`git --version`) | Available and functional |
| **Lint / Type Check** | `ruff`, `mypy` | Not installed globally | Exit 1 (`No module named ruff / mypy`)| Will be installed via virtualenv in TASK-002/006 |
| **Test Runner** | `pytest` | Not installed globally | Exit 1 (`No module named pytest`) | Will be installed via virtualenv in TASK-002/006 |

---

## 4. Directory Structure & Path Conventions

### Existing Filesystem Layout
```text
D:\grinding\Lomba\LIDM\AI_TOKI\
├── .git/                      # Git internal repository
├── AGENTS.md                  # Multi-agent operating contract (normative)
├── CURRENT_TASK.md            # Active task pointer (normative)
├── README.md                  # Project summary and developer guide
├── data/                      # (Empty directory, untracked)
├── docs/                      # Architectural, requirement, and decision records
│   ├── architecture.md        # Target system architecture
│   ├── decisions.md           # Architecture Decision Log (canonical ADR)
│   ├── evaluation.md          # Evaluation framework stub
│   ├── problem.md             # Problem definition and framing
│   ├── requirements.md        # System requirements baseline
│   └── roadmap.md             # 8-phase implementation roadmap
├── evals/                     # (Empty directory, untracked)
├── handoffs/                  # Agent state transitions
│   ├── history/
│   │   └── README.md
│   └── latest.md              # Current agent handoff state
├── scripts/                   # (Empty directory, untracked)
├── src/                       # (Empty directory, untracked)
├── tasks/                     # Task files and engineering index
│   ├── TASK-001.md .. TASK-028.md
│   ├── TASK_TEMPLATE.md
│   ├── backlog.md
│   └── index.md               # Master engineering task index
└── tests/                     # (Empty directory, untracked)
```

### Canonical Boundary Reconciliations

1. **Application Package Root (`app/` vs `src/`):**
   - *Observation:* An untracked, empty `src/` folder was present on disk.
   - *Resolution:* All task definitions (`TASK-002` through `TASK-028`), `README.md` (lines 88–147), and `docs/architecture.md` specify `app/` as the modular monolith root (e.g. `app.main:app`, `app.api`, `app.sessions`).
   - *Convention:* **`app/` is the canonical package name.** The empty `src/` directory should either be removed or ignored to prevent import confusion.

2. **Evaluation Directory (`evaluation/` vs `evals/`):**
   - *Observation:* An untracked, empty `evals/` folder was present on disk.
   - *Resolution:* All task definitions (`TASK-016`, `TASK-021`, etc.), `docs/roadmap.md`, and `README.md` designate `evaluation/` containing `evaluation/datasets/`, `evaluation/fixtures/`, and `evaluation/reports/`.
   - *Convention:* **`evaluation/` is the canonical directory.**

3. **Architecture Decision Records Path:**
   - *Observation:* `docs/decisions.md` contains ADR-001 through ADR-016. No other ADR directories or files exist in the repository.
   - *Convention:* **`docs/decisions.md` is the single canonical source of truth for architectural decisions.** Any proposed ADRs must be appended to this file.

4. **Migrations Directory (`migrations/` vs `alembic/`):**
   - *Observation:* `README.md` mentions `migrations/`, while `TASK-004` notes `alembic/versions/`.
   - *Convention:* Standard Alembic setup with `migrations/` as the Alembic script directory (or `alembic/`) with `alembic.ini` in root will be established during TASK-004.

---

## 5. Responsibility to Module Mapping & Gap Analysis

The table below maps the responsibilities outlined in `docs/architecture.md` and `docs/roadmap.md` against current repository implementations.

| Roadmap Responsibility | Target Package / Path | Required Epics / Tasks | Current Repo State | Implementation Gap & Action Required |
|---|---|---|---|---|
| **Runtime & Config** | `app/config/`, `pyproject.toml`, `.env.example` | E1 / TASK-002 | **MISSING** | Create `pyproject.toml`, dependencies, settings profiles (`test`, `local`, `cloud`, `demo_offline`). |
| **API Gateway (REST & WS)** | `app/api/` (health, sessions, progress, device WS) | E1, E4 / TASK-002, 003, 019, 020 | **MISSING** | Implement FastAPI app, router modules, lifespan handler, error formatters. |
| **Device Protocol** | `app/device_protocol/` (envelope, seq, ACK, resume) | E1, E2 / TASK-003, 008 | **MISSING** | Implement binary/JSON envelope parser, monotonic seq tracker, idempotency cache. |
| **Session FSM Orchestrator** | `app/sessions/` (states, transitions, guards, clock) | E2 / TASK-007 | **MISSING** | Implement deterministic state machine without autonomous LLM loop. |
| **Curriculum & Activity Engine**| `app/curriculum/` (metadata retrieval, approved content) | E2 / TASK-009 | **MISSING** | Implement SQL-based structured lookup, approved version checker (immutability). |
| **Answer Understanding** | `app/understanding/` (normalization, rules, phonetic) | E2 / TASK-010 | **MISSING** | Implement deterministic rules; uncertain results map to `UNCERTAIN`/`ABSTAIN`. |
| **Response Planning & Safety** | `app/response/`, `app/safety/` (templates, canned) | E2 / TASK-011 | **MISSING** | Implement template-backed `ResponsePlan`, canned escalation catalog. |
| **Persistence & Transactions** | `app/persistence/` (models, repos, UoW, outbox) | E1, E2 / TASK-004, 012 | **MISSING** | Implement SQLAlchemy async models, optimistic locking (`state_version`), atomic writes. |
| **Progress & Analytics** | `app/analytics/` (parent projection, non-clinical summary)| E2 / TASK-013 | **MISSING** | Implement read projections reconstructed from domain events. |
| **Deterministic Vertical Slice**| `app/` end-to-end text loop | E2 / TASK-014 | **MISSING** | Wire up activity loop without external AI services. |
| **Speech Adapters (ASR / TTS)** | `app/speech/` (ASR/TTS interfaces, cache, fallbacks) | E3 / TASK-015, 016, 017 | **MISSING** | Define neutral interfaces, cached audio provider, benchmark adapters. |
| **Triggered Computer Vision** | `app/vision/` (snapshot adapter, vocabulary filter) | E6 / TASK-025 | **MISSING** | Implement bounded CV observer with typed `UNKNOWN` handling. |
| **Observability & Telemetry** | `app/telemetry/` (traces, redaction, metric counters) | E2 / TASK-013, 018 | **MISSING** | Root trace per turn, zero raw audio or child PII retention in logs. |
| **Database Migrations** | `migrations/` or `alembic/` | E1 / TASK-004 | **MISSING** | Setup Alembic configuration, initial schema versions. |
| **Automated Testing Suite** | `tests/unit/`, `tests/contract/`, `tests/integration/` | E1–E7 / TASK-006, all | **MISSING** | Create test hierarchies, pytest fixtures, and contract validators. |
| **Evaluation Framework** | `evaluation/datasets/`, `evaluation/fixtures/`, `evals` | E5 / TASK-021, 022 | **MISSING** | Create golden test sets (`child-safety-300-v1`), replay harness. |
| **CI / Quality Gates** | `.github/workflows/` or equivalent | E1 / TASK-006 | **MISSING** | Create workflow running lint, typecheck, unit, and contract tests. |

---

## 6. Baseline Verification Commands & Results

To establish a reproducible baseline, documented commands from `README.md` were executed and recorded:

### 1. Version Control & Git Status
- **Command:** `git status`
- **Exit Code:** 0
- **Result:**
  ```text
  On branch main
  Your branch is up to date with 'origin/main'.
  nothing to commit, working tree clean
  ```

### 2. Python Toolchain Verification
- **Command:** `python --version`
  - **Exit Code:** 0
  - **Output:** `Python 3.13.14`
- **Command:** `uv --version`
  - **Exit Code:** CommandNotFoundException
  - **Output:** `uv : The term 'uv' is not recognized as the name of a cmdlet...`
- **Command:** `docker --version`
  - **Exit Code:** CommandNotFoundException
  - **Output:** `docker : The term 'docker' is not recognized...`

### 3. Test & Linter Execution (Pre-existing state)
- **Command:** `python -m pytest`
  - **Exit Code:** 1
  - **Output:** `No module named pytest`
  - **Classification:** Expected pre-existing failure (environment not yet bootstrapped; scheduled for TASK-002/006).
- **Command:** `python -m ruff --version`
  - **Exit Code:** 1
  - **Output:** `No module named ruff`
  - **Classification:** Expected pre-existing failure.
- **Command:** `python -m mypy --version`
  - **Exit Code:** 1
  - **Output:** `No module named mypy`
  - **Classification:** Expected pre-existing failure.

---

## 7. Requirement Traceability & Architectural Alignment

| Requirement ID | Requirement Summary | Architectural Alignment & Verification |
|---|---|---|
| **DEV-001** | Python target 3.12, FastAPI, Pydantic v2, PostgreSQL, SQLAlchemy async, Alembic. | Host currently has Python 3.13. TASK-002 will configure `pyproject.toml` targeting `>=3.12,<3.14` so both 3.12 and 3.13 are compatible. |
| **DEV-002** | Focus on single behavior, leave repository runnable. | TASK-001 maintains a non-mutating inventory, preserving repository integrity. |
| **ADR-002** | Modular monolith in single service/container. | Target structure confirmed as single application package `app/`. |
| **ADR-003** | Deterministic FSM, no runtime agents. | Session design isolated to `app/sessions/`; no agent frameworks scheduled. |
| **ADR-012** | PostgreSQL authoritative store with atomic writes and outbox. | Data layer isolated to `app/persistence/` and Alembic migrations. |
| **ADR-013** | Child-data minimization, ephemeral raw media. | Media ingestion isolated to `app/speech/ingestion.py` without persistence. |

---

## 8. Preserved Invariants & Guidance for Subsequent Tasks

For agents executing **TASK-002** through **TASK-006** (Milestone M0):

1. **Do not use `src/`:** Place all Python modules directly under `app/` (e.g. `app/main.py`, `app/config/settings.py`).
2. **Do not use `evals/`:** Use `evaluation/` for all datasets, fixtures, and replay tools.
3. **Environment Strategy for TASK-002:**
   - Because `docker` and `uv` are not presently installed in the system PATH, TASK-002 should:
     - Provide standard `pyproject.toml` compatible with `uv` and standard `pip` / `venv`.
     - Provide a virtual environment setup instructions / script that works natively on Windows using Python 3.12/3.13 while also providing `Dockerfile` and `docker-compose.yml` for containerized environments.
4. **No Premature Complexity:** Maintain the core invariant: deterministic FSM controls session flow; AI remains bounded evidence.
