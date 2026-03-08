# OrthoBraceForge

A Windows desktop application for pediatric ankle-foot orthosis (AFO) design, powered by a multi-agent AI pipeline and regulatory-grade audit logging.

## Overview

OrthoBraceForge automates the AFO design workflow for orthotists treating children with conditions such as cerebral palsy, idiopathic toe walking, and foot drop. It combines nine AI agents — covering CAD generation, finite element analysis, print defect detection, and conversational parameter refinement — into a single LangGraph-orchestrated pipeline that produces print-ready STL files with a full FDA-compliant audit trail.

## Architecture

```
main.py              Entrypoint — logging, QApplication, splash, DB init
gui.py               PyQt6 UI — 6 screens (intake → print monitoring)
orchestration.py     LangGraph state machine — routes work across agents
agents/              Per-agent wrappers (see Agent Inventory below)
compliance_rag.py    Retrieval-augmented compliance check (FDA/ISO 13485)
database.py          SQLite ORM — patient cases, design history, audit log
export.py            STL/STEP export + IFU-compliant audit PDF
fea_engine.py        FEA stress analysis for pediatric dynamic loads
config.py            App-wide constants, paths, material properties
```

See [`docs/project_structure.md`](docs/project_structure.md) for the full file tree and [`docs/architecture.mermaid`](docs/architecture.mermaid) for the pipeline diagram.

## Agent Inventory

| # | Module | Wraps | Role |
|---|--------|-------|------|
| 1 | `agents/agentic3d.py` | reetm09/agentic3d | Autogen OpenSCAD generation loop |
| 2 | `agents/forma_ai.py` | andreyka/forma-ai-service | build123d self-correction **(primary)** |
| 3 | `agents/talkcad.py` | outerreaches/talkcad | Conversational parameter refinement |
| 4 | `agents/cad_render.py` | Svetlana-DAO-LLC/cad-agent | Headless mesh rendering for VLM |
| 5 | `agents/print_defect.py` | BaratiLab/LLM-3D-Print | In-progress print defect detection |
| 6 | `agents/ortho_insoles.py` | Green-AI-Hub | Parametric AFO prediction from scans |
| 7 | `agents/octo_mcp.py` | OctoEverywhere/mcp | OctoPrint/Klipper broker |
| 8 | `agents/agentic_alloy.py` | BaratiLab/Agentic-Alloy | Ti-lattice reinforcement evaluation |
| 9 | `agents/chat_to_stl.py` | nchourrout/Chat-To-STL | Fallback STL generator |
| + | `agents/vlm_critique.py` | (internal) | VLM render-critique loop |

All agents share a `BaseAgent` contract: `execute(params) → AgentResult`. The orchestrator calls `agent.run(params)` which adds timing and structured logging around `execute()`.

## Pipeline Phases

```
INTAKE → SCAN_ANALYSIS → CAD_GENERATION → FEA → COMPLIANCE → SLICING → PRINT → DONE
```

1. **Intake** — Patient measurements entered; cross-validated against pediatric anthropometric reference ranges
2. **Scan Analysis** — OrthoInsoles agent extracts measurements from 3D scan (STL/OBJ/point cloud)
3. **CAD Generation** — FormaAI (build123d) primary; Agentic3D (OpenSCAD) fallback; ChatToSTL last resort
4. **FEA** — Stress analysis for pediatric gait loads; AgenticAlloy flags need for Ti-lattice reinforcement
5. **Compliance** — RAG-based check against FDA 21 CFR 880 / ISO 13485 / biocompatibility requirements
6. **Slicing** — G-code generated; uploaded to OctoPrint via OctoMCP
7. **Print Monitoring** — PrintDefect agent watches for under-extrusion, warping, stringing
8. **Audit PDF** — IFU-compliant report exported with full design provenance

## Installation

See [`docs/build_guide.md`](docs/build_guide.md) for full Windows build and PyInstaller packaging instructions.

### Quick Start (development)

```bash
# Python 3.11 or 3.12 required
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run
python main.py

# Tests
make test                          # or: python -m pytest tests/ -v

# Lint
make lint                          # or: python -m ruff check .
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OCTOPRINT_URL` | `http://localhost:5000` | OctoPrint instance URL |
| `OCTOPRINT_API_KEY` | *(empty)* | OctoPrint REST API key |

The API key can also be stored in the OS keyring under service `orthobraceforge`, username `octoprint_api_key`. See [`CONFIGURATION.md`](CONFIGURATION.md) for all configuration options.

## Testing

```bash
python -m pytest tests/ -v --tb=short
python -m pytest tests/ --cov=. --cov-report=term-missing
```

Current coverage: **76 %** across 377 tests. CI runs on Python 3.11 and 3.12 via GitHub Actions (`.github/workflows/ci.yml`).

## Regulatory Context

OrthoBraceForge produces custom Class II medical devices (FDA 21 CFR 880.3860). Every design action is written to an immutable SQLite audit log and exportable as a PDF Instructions for Use (IFU) document. The compliance RAG system checks generated designs against FDA, ISO 13485, and ISO 10993 biocompatibility requirements before slicing is permitted.

**This software is a design-aid tool. Clinical decisions remain the responsibility of the licensed orthotist.**

## Docs

| Document | Contents |
|----------|----------|
| [`docs/build_guide.md`](docs/build_guide.md) | Windows build, PyInstaller packaging |
| [`docs/project_structure.md`](docs/project_structure.md) | Full file tree |
| [`docs/workflow_example.md`](docs/workflow_example.md) | End-to-end walkthrough (6-year-old bilateral toe walker) |
| [`docs/risk_matrix.md`](docs/risk_matrix.md) | Risk analysis table |
| [`docs/architecture.mermaid`](docs/architecture.mermaid) | Pipeline diagram source |
| [`CONFIGURATION.md`](CONFIGURATION.md) | All env vars, logging, timeouts |
| [`TODO.md`](TODO.md) | Development roadmap |
