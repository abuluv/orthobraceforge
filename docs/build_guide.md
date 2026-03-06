# Deliverable 5: Build & Deployment Guide — Windows 10/11

## Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Windows | 10 21H2+ / 11 | Target OS |
| Python | 3.12.x (64-bit) | Runtime |
| Visual Studio Build Tools | 2022 | C++ extensions (VTK, OCP) |
| Git | 2.40+ | Vendored repo management |
| OpenSCAD | 2024.x (optional) | Fallback SCAD rendering |
| UPX | 4.2+ (optional) | Executable compression |

---

## Step 1 — Environment Setup

```powershell
# Create project directory
mkdir C:\Dev\OrthoBraceForge
cd C:\Dev\OrthoBraceForge

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Verify Python version
python --version  # Must show 3.12.x
```

## Step 2 — Clone & Vendor External Repositories

```powershell
# Clone the main project (or copy delivered source)
# Then vendor each dependency:
mkdir vendored

git clone https://github.com/reetm09/agentic3d.git          vendored/agentic3d_src
git clone https://github.com/andreyka/forma-ai-service.git    vendored/forma_ai_src
git clone https://github.com/outerreaches/talkcad.git         vendored/talkcad_src
git clone https://github.com/Svetlana-DAO-LLC/cad-agent.git   vendored/cad_agent_src
git clone https://github.com/nchourrout/Chat-To-STL.git       vendored/chat_to_stl_src
git clone https://github.com/OctoEverywhere/mcp.git           vendored/octo_mcp_src

git clone https://github.com/BaratiLab/LLM-3D-Print-Large-Language-Models-To-Monitor-and-Control-3D-Printing.git vendored/llm_3d_print_src
git clone https://github.com/Green-AI-Hub-Mittelstand/Training-and-Prediction-Toolbox-for-3D-Printable-Orthopedic-Insoles.git vendored/ortho_insoles_src
git clone https://github.com/BaratiLab/Agentic-Additive-Manufacturing-Alloy-Evaluation.git vendored/agentic_alloy_src

# Copy relevant modules into the wrapper structure:
# Each vendored/<pkg>/ directory already has __init__.py and wrapper
# classes from agents.py. Copy the source repo's core modules into
# each wrapper directory as needed. For example:
#   copy vendored\forma_ai_src\core\*.py vendored\forma_ai\
#   copy vendored\agentic3d_src\agents\*.py vendored\agentic3d\
```

## Step 3 — Install Dependencies

```powershell
# Install core dependencies
pip install -r requirements.txt

# build123d requires OCP (OpenCASCADE) — install via conda if pip fails:
# conda install -c conda-forge ocp

# Verify critical imports
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
python -c "import pyvista; print('PyVista OK')"
python -c "import trimesh; print('Trimesh OK')"
python -c "import reportlab; print('ReportLab OK')"
```

## Step 4 — Generate RAG Knowledge Base Files

```powershell
# The compliance_rag.py auto-generates default KB files on first run.
# To pre-generate them:
python -c "from compliance_rag import ComplianceKnowledgeBase; ComplianceKnowledgeBase()"
# This creates JSON files in assets/rag_data/
```

## Step 5 — Run Development Mode

```powershell
# Test the application before building
python main.py

# Run the test suite
python -m pytest tests/ -v
```

## Step 6 — Build with PyInstaller

```powershell
# Option A: Use the spec file (recommended)
pyinstaller orthobraceforge.spec

# Option B: Command-line build
pyinstaller --onefile --windowed ^
    --name OrthoBraceForge ^
    --icon assets\icons\app_icon.ico ^
    --add-data "assets;assets" ^
    --add-data "vendored;vendored" ^
    --hidden-import PyQt6 ^
    --hidden-import pyvista ^
    --hidden-import vtk ^
    --hidden-import trimesh ^
    --hidden-import build123d ^
    --hidden-import reportlab ^
    main.py

# Output: dist\OrthoBraceForge.exe
```

### Build Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: vtk` | Add `--collect-all vtk` to PyInstaller command |
| `OCP/build123d import fail` | Ensure conda OCP installed; add `--collect-all OCP` |
| Exe >2GB | Exclude torch/transformers if using ONNX-only inference |
| Qt plugin error on launch | Set `QT_PLUGIN_PATH` env var (handled in main.py) |
| Missing DLLs | Run `pyinstaller` from the activated venv |

## Step 7 — Test the Built Executable

```powershell
# Run the exe directly
.\dist\OrthoBraceForge.exe

# Verify:
# 1. Splash screen appears with regulatory warning
# 2. First-run disclaimer dialog shown
# 3. Patient intake form is functional
# 4. SQLite database created at %APPDATA%\OrthoBraceForge\
# 5. Can complete full pipeline with test data
```

## Step 8 — Code Signing (Medical Distribution)

> **CRITICAL for medical device software distribution.**

### 8a — Obtain a Code Signing Certificate

For medical device software, use an **Extended Validation (EV)** code signing certificate:

- **DigiCert** — Preferred for medical/FDA submissions. EV cert ~$500/year.
- **Sectigo** — Alternative EV provider.
- **Requirements:** Legal business entity, DUNS number, physical address verification.

### 8b — Sign the Executable

```powershell
# Using signtool.exe (from Windows SDK)
# EV certificates are typically on a hardware token (USB dongle)

signtool sign /tr http://timestamp.digicert.com ^
    /td sha256 /fd sha256 ^
    /n "OrthoBraceForge Medical Software" ^
    dist\OrthoBraceForge.exe

# Verify signature
signtool verify /pa /v dist\OrthoBraceForge.exe
```

### 8c — Timestamp Considerations

Always use a timestamp server (`/tr` flag) so the signature remains valid after the certificate expires. For FDA submissions, signatures must be verifiable indefinitely.

## Step 9 — Deployment Package

```powershell
# Create distribution folder
mkdir release\OrthoBraceForge_v1.0.0
copy dist\OrthoBraceForge.exe release\OrthoBraceForge_v1.0.0\
copy README.md release\OrthoBraceForge_v1.0.0\
copy docs\risk_matrix.md release\OrthoBraceForge_v1.0.0\

# Create installer (optional — Inno Setup)
# iscc installer.iss
```

## Step 10 — Post-Deployment Checklist

- [ ] Exe runs on clean Windows 10/11 machine without Python installed
- [ ] No internet connection required after install
- [ ] SQLite database created on first launch
- [ ] Regulatory disclaimer shown on first run
- [ ] Full pipeline completes with test patient data
- [ ] Audit PDF generates with all sections populated
- [ ] STL export produces valid, watertight mesh
- [ ] Human review gate cannot be bypassed
- [ ] Code signing signature verifies correctly
- [ ] Application logs written to `%APPDATA%\OrthoBraceForge\logs\`

---

## Notes on FDA Submission

If pursuing 510(k) clearance for this software:

1. **Software Level of Concern:** Major (generates device geometry used for patient treatment)
2. **IEC 62304 Classification:** Class B (could contribute to hazardous situation)
3. **Required Documentation:**
   - Software Development Plan
   - Software Requirements Specification
   - Software Architecture Document (Deliverable 1)
   - Software Design Specification (source code — Deliverable 3)
   - Risk Analysis (Deliverable 6)
   - Verification & Validation protocols
   - Traceability matrix (requirements → code → tests)
4. **Cybersecurity:** FDA guidance on cybersecurity in medical devices applies. The offline-only architecture simplifies this.
5. **Predicate Device:** Traditional polypropylene AFOs manufactured by conventional means (21 CFR 890.3475)
