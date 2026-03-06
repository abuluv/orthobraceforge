# OrthoBraceForge — Project Structure

```
OrthoBraceForge/
│
├── main.py                          # Entrypoint (sys.exit, QApplication, splash)
├── gui.py                           # All PyQt6 screens (6 screens + dialogs)
├── orchestration.py                 # LangGraph state machine + all agent routing
├── agents.py                        # Wrapper classes for every vendored repo
├── compliance_rag.py                # Domain RAG: FDA/ISO 13485/biocompat KB
├── database.py                      # SQLite ORM (patient cases, audit, logs)
├── export.py                        # STL/STEP export + audit PDF generation
├── fea_engine.py                    # FEA stress analysis (pediatric loads)
├── print_bridge.py                  # MCP local broker + slicer interface
├── config.py                        # App-wide constants, paths, feature flags
├── resources.qrc                    # Qt resource file
│
├── vendored/                        # All external repos vendored as packages
│   ├── __init__.py
│   ├── agentic3d/                   # reetm09/agentic3d
│   │   ├── __init__.py
│   │   ├── agent_loop.py            # Autogen OpenSCAD agent loop adapter
│   │   └── scad_templates/          # Parametric AFO SCAD templates
│   │
│   ├── forma_ai/                    # andreyka/forma-ai-service
│   │   ├── __init__.py
│   │   ├── build123d_gen.py         # build123d code gen + self-correction
│   │   └── correction_loop.py       # Control-flow self-correction engine
│   │
│   ├── talkcad/                     # outerreaches/talkcad
│   │   ├── __init__.py
│   │   ├── conversational.py        # NL→CAD orchestrator
│   │   └── preview_hook.py          # Preview integration adapter
│   │
│   ├── cad_agent/                   # Svetlana-DAO-LLC/cad-agent
│   │   ├── __init__.py
│   │   ├── render_server.py         # Headless render via subprocess
│   │   └── mesh_utils.py            # Mesh loading/conversion utilities
│   │
│   ├── llm_3d_print/               # BaratiLab/LLM-3D-Print-…
│   │   ├── __init__.py
│   │   ├── defect_monitor.py        # Print defect detection + correction
│   │   └── models/                  # Pre-trained defect weights (bundled)
│   │
│   ├── ortho_insoles/               # Green-AI-Hub…/Training-and-Prediction-Toolbox
│   │   ├── __init__.py
│   │   ├── afo_predictor.py         # Adapted: insole→AFO parametric prediction
│   │   ├── scan_processor.py        # STL/OBJ/point cloud → measurement extraction
│   │   └── models/                  # Pre-trained prediction weights (bundled)
│   │
│   ├── octo_mcp/                    # OctoEverywhere/mcp
│   │   ├── __init__.py
│   │   ├── mcp_broker.py            # Local MCP server/broker
│   │   └── printer_protocol.py      # OctoPrint/Klipper protocol adapter
│   │
│   ├── agentic_alloy/               # BaratiLab/Agentic-Additive-Manufacturing-…
│   │   ├── __init__.py
│   │   ├── lattice_evaluator.py     # Ti lattice reinforcement evaluation
│   │   └── material_db.py           # Biocompatible material database
│   │
│   └── chat_to_stl/                 # nchourrout/Chat-To-STL
│       ├── __init__.py
│       └── fallback_gen.py          # NL→STL fallback generator
│
├── assets/
│   ├── icons/
│   │   ├── app_icon.ico
│   │   ├── patient.svg
│   │   ├── brace.svg
│   │   ├── print.svg
│   │   └── audit.svg
│   ├── themes/
│   │   ├── dark.qss                 # Dark theme stylesheet
│   │   └── high_contrast.qss        # WCAG AA high-contrast stylesheet
│   └── rag_data/
│       ├── fda_510k_afo.json        # FDA 510(k) clearance knowledge base
│       ├── iso13485_checklist.json   # ISO 13485 QMS checklist
│       ├── biocompat_pediatric.json  # Biocompatibility data for pediatric AFOs
│       ├── equinus_clinical.json     # Idiopathic toe walking clinical parameters
│       └── material_specs.json       # PETG / Nylon / TPU / Ti6Al4V material specs
│
├── tests/
│   ├── test_orchestration.py
│   ├── test_agents.py
│   ├── test_compliance.py
│   ├── test_fea.py
│   └── test_e2e_toewalk.py          # End-to-end 6yo bilateral toe walker test
│
├── docs/
│   ├── architecture.mermaid          # System architecture diagram
│   ├── build_guide.md               # Build & deployment instructions
│   ├── risk_matrix.md               # Pediatric medical use risk matrix
│   └── workflow_example.md          # 6yo bilateral toe walker walkthrough
│
├── orthobraceforge.spec             # PyInstaller spec file
├── requirements.txt
├── pyproject.toml
└── README.md
```
