# OrthoBraceForge — Codebase Review & Multiphase TODO List

## Context

**OrthoBraceForge** is a PyQt6 desktop application for designing and manufacturing pediatric Ankle-Foot Orthoses (AFOs) for children with toe-walking conditions (ages 2–12). It features a LangGraph-style 11-phase agentic orchestration pipeline integrating 9 vendored CAD/AI repositories, compliance RAG, VLM-based design critique, FEA, and OctoPrint-based manufacturing.

At ~4,447 lines of Python across 8 core modules, the software is classified as a **Class II Medical Device Design Tool** (investigational, not FDA-cleared), which makes reliability, security, and auditability especially critical.

This review identified significant gaps in test coverage, security hardening, feature completeness, and developer infrastructure. The todo list below is organized into sequential phases ordered by risk and dependency.

---

## Phase 1: Critical Stability & Security Fixes
> **Priority: Immediate — Blocks production use**

### 1.1 Implement Stub Methods in `agents.py`
- [ ] Implement `OctoMCPAgent._upload_gcode()` — currently only checks file existence, does not actually upload to OctoPrint API (`agents.py:904`)
- [ ] Implement `OctoMCPAgent._start_print()` — currently a stub that logs and returns `True` without issuing an API call (`agents.py:906–909`)
- [ ] Review and harden `TalkCADAgent` fallback path for unrecognized instructions (`agents.py:599–600`)

### 1.2 Fix Security Issues in `agents.py`
- [ ] Add API key validation before OctoPrint calls — raise `ValueError` if `_api_key` is empty (`agents.py:845`)
- [ ] Switch OctoPrint communication from `http://` to `https://` or make protocol configurable in `config.py`
- [ ] Add path sanitization / `Path.resolve()` + allowlist check before writing files to `EXPORT_DIR` (multiple locations in `agents.py` and `export.py`)
- [ ] Validate subprocess inputs (OpenSCAD command args, Python script paths) to prevent PATH hijacking (`agents.py:266–268`, `471–473`)

### 1.3 Replace Wildcard Import in `agents.py`
- [ ] Replace `from build123d import *` (line 379) with explicit named imports to improve auditability and avoid namespace pollution

### 1.4 Extract Magic Numbers to `config.py`
- [ ] Move OpenSCAD subprocess timeout `120` → `OPENSCAD_TIMEOUT_SEC` in `config.py` (`agents.py:268`)
- [ ] Move build123d subprocess timeout `180` → `BUILD123D_TIMEOUT_SEC` in `config.py` (`agents.py:473`)
- [ ] Move OctoPrint connection timeout `5` → `OCTOPRINT_CONNECT_TIMEOUT_SEC` in `config.py` (`agents.py:895`)
- [ ] Move AFO dimension validation bounds (`100`, `400`, `80`, `350`) to named constants in `config.py` (`agents.py:503–506`)

---

## Phase 2: Test Coverage
> **Priority: High — Required for medical device software compliance**

### 2.1 Set Up Test Infrastructure
- [ ] Add `pytest` and `pytest-qt` to dev dependencies (`pyproject.toml` / `requirements-dev.txt`)
- [ ] Create `conftest.py` with shared fixtures (mock database, mock OctoPrint server, sample patient data)
- [ ] Add `pytest.ini` or `[tool.pytest]` section configuring test paths and coverage reporting

### 2.2 Unit Tests — Core Modules
- [ ] Write unit tests for `config.py` — verify presets, material specs, and anthropometric table values are consistent
- [ ] Write unit tests for `database.py` — CRUD operations for `PatientRecord`, `DesignRecord`, `AuditEntry`
- [ ] Write unit tests for `export.py` — STL export, PDF report generation, audit trail attachment
- [ ] Write unit tests for `compliance_rag.py` — RAG retrieval accuracy and compliance flag triggers

### 2.3 Unit Tests — Agent Layer (`agents.py`)
- [ ] Test `FormaAIAgent` — parametric AFO parameter generation from scan data
- [ ] Test `Agentic3DAgent` — CAD script generation and validation
- [ ] Test `OctoMCPAgent` — mock OctoPrint API interactions (upload, start, status polling)
- [ ] Test `VLMCritiqueAgent` — critique loop termination and output parsing
- [ ] Test `AgenticAlloyAgent` — lattice evaluation logic
- [ ] Test `OrthoInsolesAgent` — insole geometry computation
- [ ] Test `PrintDefectAgent` — defect detection on mock render images
- [ ] Test input validation in each agent's `execute()` method

### 2.4 Integration Tests — Orchestration Pipeline (`orchestration.py`)
- [ ] Write end-to-end pipeline test: patient intake → compliance → parametric → CAD generation → export (mocking LLM and OctoPrint calls)
- [ ] Test each phase transition and `Phase` enum state machine edges
- [ ] Test error recovery: inject failures at each phase, verify `Phase.ERROR` state and audit log
- [ ] Test `HUMAN_REVIEW_REQUIRED` gate — ensure pipeline halts without approval signal

### 2.5 GUI Smoke Tests (`gui.py`)
- [ ] Use `pytest-qt` to verify main window opens without errors
- [ ] Test patient form validation — invalid age, out-of-range measurements
- [ ] Test workflow trigger buttons reach orchestration correctly

---

## Phase 3: Error Handling & Observability
> **Priority: Medium — Reliability and debuggability**

### 3.1 Create Custom Exception Hierarchy
- [ ] Define `OrthoError(Exception)` base class and domain-specific subclasses in a new `exceptions.py`:
  - `ComplianceError` — regulatory/compliance failures
  - `CADGenerationError` — CAD script execution failures
  - `PrinterConnectionError` — OctoPrint connectivity issues
  - `MeasurementValidationError` — patient data out of range
- [ ] Replace broad `except Exception` blocks (12+ locations in `agents.py`) with specific exception types

### 3.2 Improve Logging
- [ ] Add structured JSON logging option for audit trail integration
- [ ] Ensure all agent `execute()` methods log start/end timestamps with `run_id` and `patient_id`
- [ ] Add log rotation configuration (max size, backup count) to `main.py:setup_logging()`
- [ ] Surface agent-level errors in the GUI status bar (currently may be silently swallowed)

### 3.3 API Key Configuration Security
- [ ] Document secure API key configuration (environment variable vs. encrypted keyring) in a `CONFIGURATION.md`
- [ ] Add startup check that warns (not crashes) if OctoPrint API key is unconfigured
- [ ] Consider using `keyring` library for OS-level secure credential storage

---

## Phase 4: Feature Completeness
> **Priority: Medium — Complete the intended design**

### 4.1 OctoPrint Integration (Complete Stubs)
- [ ] Implement full OctoPrint REST API client in `agents.py` or extract to `octoprint_client.py`:
  - `POST /api/files/local` — file upload with multipart form data
  - `POST /api/job` — start/stop/pause print job
  - `GET /api/printer` — real-time temperature and state polling
  - `GET /api/job` — print progress monitoring
- [ ] Add print progress callback to GUI progress panel

### 4.2 FEA Integration
- [ ] Verify `AgenticAlloyAgent` FEA simulation is fully implemented — confirm it produces Von Mises stress results against `FEA_DEFAULTS` (`config.py:194–200`)
- [ ] Add FEA result visualization to GUI (stress heatmap or tabular summary)
- [ ] Export FEA report as part of the audit trail PDF

### 4.3 Patient Measurement Validation
- [ ] Cross-validate entered foot length and ankle width against `PEDIATRIC_ANTHRO` reference ranges for the entered patient age (`config.py:175–188`)
- [ ] Show GUI warning (not hard block) when measurements deviate >2 standard deviations from age norms
- [ ] Document the validation logic and acceptable ranges in the UI tooltip or help text

### 4.4 Multi-Patient Workflow
- [ ] Add patient search / filtering to the patient list in `gui.py`
- [ ] Support loading a previous design for re-iteration (currently appears to always start fresh)
- [ ] Add design comparison view — show two designs side-by-side for revision tracking

---

## Phase 5: Code Quality & Maintainability
> **Priority: Low-Medium — Technical debt reduction**

### 5.1 Refactor `agents.py`
- [ ] Split `agents.py` (1,131 lines) into per-agent modules: `agents/forma_ai.py`, `agents/agentic3d.py`, etc.
- [ ] Define `AgentBase` abstract class in `agents/base.py` with enforced `execute()` signature, input schema, and output schema

### 5.2 Refactor `gui.py`
- [ ] Split `gui.py` (1,202 lines) into sub-panels: `gui/patient_panel.py`, `gui/design_panel.py`, `gui/print_panel.py`
- [ ] Extract stylesheet/theme strings to `assets/themes/` QSS files (some are likely inline)

### 5.3 Type Annotations
- [ ] Add `mypy` to dev tooling; fix any type errors in `orchestration.py` and `agents.py`
- [ ] Ensure `PipelineState` TypedDict fields are consistently typed across all orchestration nodes

### 5.4 Dependency Management
- [ ] Audit vendored repos in `vendored/` — each has only an `__init__.py`; document what each provides and whether it can be replaced by a PyPI package
- [ ] Create `requirements.txt` and `requirements-dev.txt` with pinned versions
- [ ] Add `pyproject.toml` with project metadata (name, version, Python constraint, entrypoint)

---

## Phase 6: Developer Infrastructure & CI/CD
> **Priority: Low — Sustains long-term development velocity**

### 6.1 Documentation
- [ ] Write `README.md` covering: project overview, architecture diagram, installation, usage, developer setup
- [ ] Add `CONFIGURATION.md` documenting all `config.py` settings and environment variables
- [ ] Add `ARCHITECTURE.md` documenting the 11-phase orchestration pipeline with a Mermaid state diagram

### 6.2 CI Pipeline (GitHub Actions)
- [ ] Add `.github/workflows/ci.yml` with: lint (`ruff`), type check (`mypy`), test (`pytest`) on Python 3.11+
- [ ] Add coverage reporting (fail if < 70% coverage on core modules)
- [ ] Add a `pre-commit` config with `ruff`, `black`, and `mypy` hooks

### 6.3 Build & Packaging
- [ ] Review and update PyInstaller spec file (if present) for packaging to Windows `.exe`
- [ ] Add a `build.sh` / `Makefile` with common dev tasks: `make test`, `make lint`, `make build`
- [ ] Ensure frozen-exe path fixup in `main.py` is covered by a smoke test

---

## Key Files Reference

| File | Lines | Phase |
|---|---|---|
| `agents.py` | 1,131 | 1, 2, 3, 4, 5 |
| `gui.py` | 1,202 | 2, 4, 5 |
| `orchestration.py` | 733 | 2, 3 |
| `compliance_rag.py` | 507 | 2 |
| `export.py` | 245 | 1, 2 |
| `database.py` | 299 | 2 |
| `config.py` | 211 | 1 |
| `main.py` | 119 | 3, 6 |

---

## Verification Checklist

After completing all phases:
- [ ] Run `pytest --cov=. --cov-report=term-missing` and achieve ≥ 70% coverage
- [ ] Run `mypy agents.py orchestration.py` with zero errors
- [ ] Run `ruff check .` with zero violations
- [ ] Launch the application (`python main.py`) and complete a full patient → export workflow manually
- [ ] Verify OctoPrint upload and print-start work against a live or mock OctoPrint server
- [ ] Confirm audit trail PDF is generated and includes FEA results
- [ ] Confirm compliance RAG correctly flags out-of-spec designs
