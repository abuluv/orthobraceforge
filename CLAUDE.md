# CLAUDE.md — OrthoBraceForge

## Project Overview

OrthoBraceForge is a **Pediatric AFO (Ankle-Foot Orthosis) Design & Manufacturing Suite** for idiopathic toe walking (equinus gait). It uses an agentic LangGraph-style pipeline to go from patient intake to 3D-printable STL output, with mandatory regulatory compliance checks and human clinician review gates.

**Classification:** Investigational Use Only — NOT FDA Cleared (21 CFR 890.3475)

## Tech Stack

- **Language:** Python 3.11+ (target 3.11–3.12)
- **GUI:** PyQt6
- **3D/CAD:** pyvista, trimesh, build123d, OpenSCAD (via subprocess)
- **ML/Inference:** sentence-transformers (RAG embeddings), numpy, scipy, scikit-learn, onnxruntime
- **Agent Orchestration:** Manual LangGraph-style state machine (not the langgraph library directly, for PyInstaller compatibility)
- **Database:** SQLite with WAL mode, parameterized queries
- **PDF Reports:** reportlab
- **Printer Integration:** OctoPrint REST API
- **Packaging:** PyInstaller (see `orthobraceforge.spec`)

## Repository Structure

```
orthobraceforge/
├── main.py                 # Application entrypoint (Qt app launch, logging setup)
├── config.py               # All paths, feature flags, clinical constants, material specs
├── orchestration.py         # LangGraph-style pipeline orchestrator (11 phases)
├── database.py              # SQLite layer: patients, designs, audit trail (ISO 13485)
├── compliance_rag.py        # RAG engine for FDA/ISO/biocompatibility compliance
├── export.py                # Audit PDF generator (reportlab)
├── exceptions.py            # Domain exception hierarchy (OrthoError base)
├── agents/                  # Agent wrappers for vendored integrations
│   ├── __init__.py          # Re-exports all agents
│   ├── base.py              # BaseAgent ABC + AgentResult dataclass
│   ├── forma_ai.py          # build123d CAD generation (preferred engine)
│   ├── agentic3d.py         # OpenSCAD CAD generation (fallback)
│   ├── chat_to_stl.py       # LLM-to-STL fallback (lowest fidelity)
│   ├── talkcad.py           # NL-to-CAD interpretation
│   ├── cad_render.py        # Headless mesh rendering (pyvista)
│   ├── vlm_critique.py      # Vision-language model design critique
│   ├── ortho_insoles.py     # Foot scan parametric prediction
│   ├── agentic_alloy.py     # Ti lattice reinforcement evaluation
│   ├── print_defect.py      # 3D print defect detection
│   └── octo_mcp.py          # OctoPrint MCP broker
├── gui/                     # PyQt6 GUI screens
│   ├── __init__.py          # Re-exports all screens
│   ├── main_window.py       # Main window with stacked widget navigation
│   ├── patient_panel.py     # Patient intake + condition selector screens
│   ├── design_panel.py      # 3D preview, generation progress, compliance report
│   ├── print_panel.py       # Export/print queue + human review dialog
│   ├── worker.py            # QThread-based pipeline worker
│   └── theme.py             # Dark and high-contrast theme stylesheets
├── vendored/                # Placeholder stubs for 9 external repos (see vendored/README.md)
├── assets/
│   └── rag_data/            # Bundled JSON knowledge bases for compliance RAG
├── tests/                   # pytest test suite
│   ├── conftest.py          # Shared fixtures (tmp_db, sample data)
│   ├── test_database.py
│   ├── test_orchestration.py
│   ├── test_agents.py
│   ├── test_compliance_rag.py
│   ├── test_config.py
│   ├── test_exceptions.py
│   └── test_export.py
├── docs/                    # Documentation
├── .github/workflows/ci.yml # CI: lint + test on Python 3.11/3.12
├── pyproject.toml           # Project metadata, ruff/mypy/pytest config
├── Makefile                 # Dev commands (test, lint, typecheck, coverage)
├── requirements.txt         # Full runtime dependencies
├── requirements-dev.txt     # Dev dependencies (pytest, ruff, mypy)
└── orthobraceforge.spec     # PyInstaller build spec
```

## Development Commands

```bash
# Install
make install          # pip install -r requirements.txt
make install-dev      # install both runtime + dev deps

# Testing
make test             # python -m pytest -q
make coverage         # pytest --cov --cov-fail-under=70

# Linting
make lint             # ruff check .
make lint-fix         # ruff check --fix .

# Type Checking
make typecheck        # mypy on core modules (orchestration, agents/base, compliance_rag, database, config)

# Cleanup
make clean            # remove __pycache__, .pytest_cache, coverage artifacts
```

## Pipeline Architecture

The orchestrator (`OrchoBraceOrchestrator` in `orchestration.py`) runs an 11-phase state machine:

1. **INTAKE** — Parse patient data, create DB records, validate measurements against age norms
2. **COMPLIANCE** — RAG check against FDA/ISO/biocompatibility knowledge base
3. **PARAMETRIC** — Extract AFO parameters from foot scan (OrthoInsolesAgent)
4. **CAD_GEN** — Generate CAD with fallback chain: build123d → OpenSCAD → Chat-To-STL
5. **RENDER** — Headless pyvista render for visual inspection
6. **VLM_CRITIQUE** — Vision-language model critique loop (up to 5 rounds)
7. **FEA** — Finite element stress analysis (simplified beam model)
8. **LATTICE** — Titanium lattice reinforcement evaluation
9. **HUMAN_REVIEW** — **MANDATORY** clinician approval gate (never bypass)
10. **EXPORT** — STL/STEP export + audit PDF generation
11. **PRINT** — Optional OctoPrint queue via MCP broker

State flows through `PipelineState` (TypedDict) across all phases.

## Key Conventions

### Code Style
- **Linter:** ruff (rules: E, F, W, I; E501 ignored)
- **Line length:** 120 characters
- **Import sorting:** isort via ruff, first-party modules defined in `pyproject.toml`
- **Type checking:** mypy with `ignore_missing_imports = true` for vendored/optional deps
- **Python version target:** 3.11

### Agent Pattern
All agents extend `BaseAgent` (in `agents/base.py`):
- Implement `execute(params: Dict[str, Any]) -> AgentResult`
- Use `self._log()` for trace logging
- The `run()` wrapper handles timing and error logging automatically
- Return `AgentResult` with `success`, `output_data`, `output_files`, `errors`, `warnings`, `trace_log`
- Agent names correspond to keys in `OrchoBraceOrchestrator.agents` dict

### Database
- SQLite with WAL journal mode and foreign keys enabled
- All records use UUID primary keys
- Full audit trail via `audit_log` table (every create, modify, review, approve, export, print action)
- Parameterized queries throughout — **never** use f-string SQL
- Dataclasses: `PatientRecord`, `DesignRecord`, `AuditEntry`

### Exception Hierarchy
```
OrthoError (base)
├── ComplianceError        — Regulatory check failures
├── CADGenerationError     — CAD script generation/execution failures (includes engine field)
├── PrinterConnectionError — OctoPrint connectivity issues
└── MeasurementValidationError — Patient measurements out of range (includes field, value, valid_range)
```
All exceptions accept optional `context: Dict` for structured error metadata.

### Testing
- Framework: pytest with `pythonpath = ["."]`
- Fixtures in `tests/conftest.py`: `tmp_db`, `sample_patient_data`, `sample_patient_record`, `sample_design_record`, `mock_pipeline_state`
- Tests use `tmp_path` for isolated SQLite databases
- Coverage target: 70% minimum
- CI runs on Python 3.11 and 3.12

### Configuration
All application constants live in `config.py`:
- Path resolution handles both dev mode and PyInstaller frozen mode
- Clinical presets in `TOE_WALKING_PRESETS` dict (keyed by severity)
- Material specs in `MATERIALS` dict (PETG, Nylon PA12, TPU, Ti-6Al-4V)
- Pediatric anthropometric ranges in `PEDIATRIC_ANTHRO` (ages 2–12)
- FEA defaults require safety factor >= 3.0 for pediatric devices
- `HUMAN_REVIEW_REQUIRED = True` — **NEVER set False in production**

## Critical Safety Rules

1. **Human review gate is mandatory.** `HUMAN_REVIEW_REQUIRED` must always be `True` in production. The pipeline enforces clinician approval before any design can be exported or printed.
2. **Never bypass compliance checks.** The RAG compliance engine checks FDA 21 CFR 890.3475, ISO 13485, and ISO 10993 requirements. Blocking issues halt the pipeline.
3. **Parameterized SQL only.** Never construct SQL with f-strings or string concatenation.
4. **Audit trail integrity.** Every state-changing action must be logged to `audit_log` with actor identification.
5. **No patient data in logs/errors.** Use truncated IDs (`patient_id[:8]`) when logging.
6. **Safety factor >= 3.0** for all pediatric device FEA validation.

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- **test job:** Matrix build on Python 3.11 + 3.12, installs dev deps, runs ruff check and pytest with 70% coverage gate
- **lint job:** Dedicated ruff check on Python 3.12

## Vendored Dependencies

The `vendored/` directory contains stub `__init__.py` files for 9 external repositories. These are integration points — actual logic lives in corresponding `agents/*.py` wrappers. See `vendored/README.md` for the full inventory and integration status. Some stubs can be replaced with PyPI packages (build123d, pyvista, trimesh).
