# OrthoBraceForge — Codebase Review & Multiphase TODO List

## Context

**OrthoBraceForge** is a PyQt6 desktop application for designing and manufacturing pediatric Ankle-Foot Orthoses (AFOs) for children with toe-walking conditions (ages 2–12). It features a LangGraph-style 11-phase agentic orchestration pipeline integrating 9 vendored CAD/AI repositories, compliance RAG, VLM-based design critique, FEA, and OctoPrint-based manufacturing.

At ~4,447 lines of Python across 8 core modules, the software is classified as a **Class II Medical Device Design Tool** (investigational, not FDA-cleared), which makes reliability, security, and auditability especially critical.

This review identified significant gaps in test coverage, security hardening, feature completeness, and developer infrastructure. The todo list below is organized into sequential phases ordered by risk and dependency.

---

## Phase 1: Critical Stability & Security Fixes ✅
> **Priority: Immediate — Blocks production use**
> **Status: COMPLETED** — merged to main

### 1.1 Implement Stub Methods in `agents.py` ✅
- [x] Implement `OctoMCPAgent._upload_gcode()` — multipart POST to `/api/files/local`
- [x] Implement `OctoMCPAgent._start_print()` — POST to `/api/job`
- [x] Review and harden `TalkCADAgent` fallback path for unrecognized instructions

### 1.2 Fix Security Issues in `agents.py` ✅
- [x] Add API key validation before OctoPrint calls — raises `ValueError` if `_api_key` is empty
- [x] OctoPrint protocol is configurable via `OCTOPRINT_URL` in `config.py`
- [x] Add path sanitization / `Path.resolve()` + EXPORT_DIR allowlist check in `_upload_gcode()`
- [x] Subprocess inputs validated via parametric template (no user-controlled command args)

### 1.3 Replace Wildcard Import in `agents.py` ✅
- [x] Replaced with explicit named imports in `agents/forma_ai.py` code template

### 1.4 Extract Magic Numbers to `config.py` ✅
- [x] `OPENSCAD_TIMEOUT_SEC`, `BUILD123D_TIMEOUT_SEC`, `OCTOPRINT_CONNECT_TIMEOUT_SEC` in config.py
- [x] `AFO_LENGTH_MIN_MM`, `AFO_LENGTH_MAX_MM`, `AFO_HEIGHT_MIN_MM`, `AFO_HEIGHT_MAX_MM` in config.py

---

## Phase 2: Test Coverage ✅
> **Priority: High — Required for medical device software compliance**
> **Status: COMPLETED** — merged to main (377 tests, 76% coverage)

### 2.1 Set Up Test Infrastructure ✅
- [x] pytest, pytest-cov, pytest-qt in dev dependencies
- [x] `conftest.py` with shared fixtures (mock database, sample patient data)
- [x] `[tool.pytest]` section in `pyproject.toml`

### 2.2 Unit Tests — Core Modules ✅
- [x] Tests for `config.py`, `database.py`, `export.py`, `compliance_rag.py`

### 2.3 Unit Tests — Agent Layer ✅
- [x] Tests for all 10 agent classes covering execute(), error paths, and input validation

### 2.4 Integration Tests — Orchestration Pipeline ✅
- [x] End-to-end pipeline tests, phase transitions, error recovery, measurement validation

### 2.5 GUI Smoke Tests
- [ ] Blocked — requires display server for pytest-qt; deferred to manual testing

---

## Phase 3: Error Handling & Observability ✅
> **Priority: Medium — Reliability and debuggability**
> **Status: COMPLETED** — commit `ff3cc8e`

### 3.1 Custom Exception Hierarchy ✅
- [x] `exceptions.py`: `OrthoError`, `ComplianceError`, `CADGenerationError`, `PrinterConnectionError`, `MeasurementValidationError`
- [x] All 11 `except Exception` blocks replaced with specific exception types + narrow safety nets
- [x] 21 tests in `test_exceptions.py`

### 3.2 Improved Logging ✅
- [x] `JsonFormatter` class with structured JSON logging option
- [x] `BaseAgent.run()` wrapper: logs start/end timestamps with `run_id` and `patient_id`
- [x] `RotatingFileHandler` with `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT` config
- [x] Agent errors surfaced in GUI status bar via `error_occurred` signal

### 3.3 API Key Configuration Security ✅
- [x] `CONFIGURATION.md` documents env vars, keyring setup, logging config
- [x] Startup warning if OctoPrint API key is unconfigured
- [x] `keyring` fallback in `OctoMCPAgent.__init__`

---

## Phase 4: Feature Completeness (Partial)
> **Priority: Medium — Complete the intended design**
> **Status: 4.1 done (OctoPrint REST client), 4.3 done (measurement validation)**

### 4.1 OctoPrint Integration ✅
- [x] Full REST client: `POST /api/files/local`, `POST /api/job`, `GET /api/printer`
- [ ] Print progress polling via `GET /api/job` — not yet wired to GUI progress panel

### 4.2 FEA Integration
- [ ] Add FEA result visualization to GUI (stress heatmap or tabular summary)
- [ ] Export FEA report as part of the audit trail PDF

### 4.3 Patient Measurement Validation ✅
- [x] `_validate_measurements()` cross-validates against `PEDIATRIC_ANTHRO` reference ranges
- [x] Warnings emitted (not hard blocks) for out-of-range measurements
- [x] 5 tests in `TestMeasurementValidation`

### 4.4 Multi-Patient Workflow
- [ ] Patient search / filtering in GUI patient list
- [ ] Load previous design for re-iteration
- [ ] Design comparison view (side-by-side revision tracking)

---

## Phase 5: Code Quality & Maintainability ✅
> **Priority: Low-Medium — Technical debt reduction**
> **Status: COMPLETED**

### 5.1 Refactor `agents.py` → `agents/` package ✅
- [x] Split 1,261-line `agents.py` into 10 per-agent modules under `agents/`
- [x] `agents/base.py`: `AgentResult` + `BaseAgent` with `run()` wrapper
- [x] `agents/__init__.py` re-exports all classes for backward compatibility

### 5.2 Refactor `gui.py` → `gui/` package ✅
- [x] Split 1,227-line `gui.py` into `theme.py`, `worker.py`, `patient_panel.py`, `design_panel.py`, `print_panel.py`, `main_window.py`
- [x] `gui/__init__.py` re-exports all classes for backward compatibility

### 5.3 Type Annotations ✅
- [x] mypy added to dev tooling (`pyproject.toml`, `requirements-dev.txt`, `Makefile`)
- [x] Type errors fixed in `config.py`, `database.py`, `compliance_rag.py`, `orchestration.py`, `agents/`
- [x] Core modules pass `mypy --ignore-missing-imports` with zero errors

### 5.4 Dependency Management ✅
- [x] Vendored repos audited — documented in `vendored/README.md`
- [x] `requirements.txt` and `requirements-dev.txt` present
- [x] `pyproject.toml` with project metadata, entrypoint, ruff + mypy + pytest config

---

## Phase 6: Developer Infrastructure & CI/CD ✅
> **Priority: Low — Sustains long-term development velocity**
> **Status: COMPLETED**

### 6.1 Documentation ✅
- [x] Root `README.md` — overview, architecture, agent inventory, installation, regulatory context
- [x] `CONFIGURATION.md` — all env vars, logging, timeouts, security notes
- [x] Architecture diagram already in `docs/architecture.mermaid`

### 6.2 CI Pipeline (GitHub Actions) ✅
- [x] `.github/workflows/ci.yml` — ruff lint + pytest (--cov-fail-under=70) on Python 3.11/3.12
- [ ] Add mypy to CI matrix (currently `make typecheck` only)
- [ ] Add pre-commit config (optional)

### 6.3 Build & Packaging ✅
- [x] `Makefile` with targets: `test`, `lint`, `lint-fix`, `typecheck`, `coverage`, `clean`
- [ ] Review and update PyInstaller spec file (if present) for packaging to `.exe`

---

## Remaining Work (for next session)

| Item | Phase | Effort | Notes |
|------|-------|--------|-------|
| FEA result visualization in GUI | 4.2 | Medium | Requires PyVista/display |
| FEA report in audit PDF | 4.2 | Low | Wire FEA dict into `export.py` |
| Print progress polling + GUI | 4.1 | Medium | `GET /api/job` + QTimer |
| Multi-patient workflow | 4.4 | High | Search, filter, design comparison |
| GUI smoke tests (pytest-qt) | 2.5 | Medium | Blocked without display server |
| mypy in CI | 6.2 | Low | Add step to ci.yml |
| PyInstaller spec review | 6.3 | Low | May not have spec file |

---

## Key Files Reference

| File | Lines | Status |
|---|---|---|
| `agents/` (package) | ~1,370 | ✅ Split from monolithic `agents.py` |
| `gui/` (package) | ~1,300 | ✅ Split from monolithic `gui.py` |
| `orchestration.py` | ~750 | ✅ Error handling, measurement validation |
| `compliance_rag.py` | ~510 | ✅ Type fixes |
| `export.py` | ~245 | ✅ Ruff fixes |
| `database.py` | ~300 | ✅ Type annotation |
| `config.py` | ~220 | ✅ Logging constants, type fix |
| `main.py` | ~120 | ✅ JSON logging, startup warning |
| `exceptions.py` | ~65 | ✅ New — custom exception hierarchy |

---

## Verification Checklist

- [x] Run `pytest --cov=. --cov-report=term-missing` and achieve ≥ 70% coverage → **76%**
- [x] Run `mypy` on core modules with zero errors → **Success: 0 errors**
- [x] Run `ruff check .` with zero violations → **All checks passed**
- [ ] Launch the application (`python main.py`) and complete a full patient → export workflow manually
- [ ] Verify OctoPrint upload and print-start work against a live or mock OctoPrint server
- [ ] Confirm audit trail PDF is generated and includes FEA results
- [ ] Confirm compliance RAG correctly flags out-of-spec designs
