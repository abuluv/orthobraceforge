# -*- mode: python ; coding: utf-8 -*-
# OrthoBraceForge.spec — PyInstaller single-exe build specification
# Usage: pyinstaller orthobraceforge.spec
# Requires: Python 3.12, PyInstaller >= 6.0

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
BASE_DIR = os.path.abspath(os.path.dirname(SPEC))

# ---------------------------------------------------------------------------
# Collect all vendored submodule packages
# ---------------------------------------------------------------------------
vendored_hiddenimports = []
for pkg in [
    "vendored.agentic3d",
    "vendored.forma_ai",
    "vendored.talkcad",
    "vendored.cad_agent",
    "vendored.llm_3d_print",
    "vendored.ortho_insoles",
    "vendored.octo_mcp",
    "vendored.agentic_alloy",
    "vendored.chat_to_stl",
]:
    vendored_hiddenimports += collect_submodules(pkg)

# Core hidden imports for the tech stack
core_hiddenimports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.sip",
    "pyvista",
    "pyvistaqt",
    "vtk",
    "numpy",
    "scipy",
    "trimesh",
    "build123d",
    "cadquery",
    "OCP",
    "stl",
    "sqlite3",
    "reportlab",
    "langgraph",
    "langchain",
    "langchain_core",
    "langchain_community",
    "sentence_transformers",
    "torch",
    "torchvision",
    "transformers",
    "onnxruntime",
    "sklearn",
    "pandas",
    "Pillow",
    "cv2",
    "open3d",
    "flask",              # local MCP broker
    "websockets",
    "aiohttp",
    "jsonschema",
    "yaml",
    "toml",
]

all_hiddenimports = vendored_hiddenimports + core_hiddenimports

# ---------------------------------------------------------------------------
# Data / asset bundles
# ---------------------------------------------------------------------------
datas = [
    # RAG knowledge bases
    (os.path.join(BASE_DIR, "assets", "rag_data"), "assets/rag_data"),
    # Qt stylesheets
    (os.path.join(BASE_DIR, "assets", "themes"), "assets/themes"),
    # Icons
    (os.path.join(BASE_DIR, "assets", "icons"), "assets/icons"),
    # Pre-trained model weights (defect detection)
    (os.path.join(BASE_DIR, "vendored", "llm_3d_print", "models"), "vendored/llm_3d_print/models"),
    # Pre-trained model weights (AFO predictor)
    (os.path.join(BASE_DIR, "vendored", "ortho_insoles", "models"), "vendored/ortho_insoles/models"),
    # OpenSCAD parametric templates
    (os.path.join(BASE_DIR, "vendored", "agentic3d", "scad_templates"), "vendored/agentic3d/scad_templates"),
    # Biocompatible material database
    (os.path.join(BASE_DIR, "vendored", "agentic_alloy", "material_db.py"), "vendored/agentic_alloy"),
]

# Collect additional data from installed packages
datas += collect_data_files("pyvista")
datas += collect_data_files("certifi")
datas += collect_data_files("sentence_transformers")

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [os.path.join(BASE_DIR, "main.py")],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",       # not needed; saves ~30MB
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------------
# Prune test / doc files from collected packages to reduce exe size
# ---------------------------------------------------------------------------
EXCLUDE_PATTERNS = [
    "tests",
    "test_",
    "__pycache__",
    ".git",
    "docs",
    "examples",
    "benchmarks",
]

def should_exclude(name):
    return any(pat in name for pat in EXCLUDE_PATTERNS)

a.datas = [d for d in a.datas if not should_exclude(d[0])]

# ---------------------------------------------------------------------------
# PYZ, EXE, COLLECT
# ---------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="OrthoBraceForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                   # Windowed mode — no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BASE_DIR, "assets", "icons", "app_icon.ico"),
    version_info={
        "CompanyName": "OrthoBraceForge Medical Software",
        "FileDescription": "Pediatric AFO Design & Manufacturing Suite",
        "FileVersion": "1.0.0.0",
        "InternalName": "OrthoBraceForge",
        "LegalCopyright": "© 2025 OrthoBraceForge. For investigational use.",
        "OriginalFilename": "OrthoBraceForge.exe",
        "ProductName": "OrthoBraceForge",
        "ProductVersion": "1.0.0",
    },
)
