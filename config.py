"""
OrthoBraceForge — Application Configuration
All paths, feature flags, clinical constants, and material specs.
"""
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Path resolution (works both in dev and PyInstaller frozen mode)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    USER_DATA = Path(os.environ.get("APPDATA", "~")) / "OrthoBraceForge"
else:
    BASE_DIR = Path(__file__).resolve().parent
    USER_DATA = BASE_DIR / "user_data"

USER_DATA.mkdir(parents=True, exist_ok=True)

ASSETS_DIR = BASE_DIR / "assets"
RAG_DATA_DIR = ASSETS_DIR / "rag_data"
THEMES_DIR = ASSETS_DIR / "themes"
ICONS_DIR = ASSETS_DIR / "icons"
DB_PATH = USER_DATA / "orthobraceforge.db"
EXPORT_DIR = USER_DATA / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "OrthoBraceForge"
APP_VERSION = "1.0.0"
APP_CLASSIFICATION = "INVESTIGATIONAL USE ONLY — NOT FDA CLEARED"
REGULATORY_BANNER = (
    "⚠ CAUTION: This software is classified as a Class II Medical Device Design Tool. "
    "All outputs require review by a licensed orthotist or physician before clinical use. "
    "Not cleared by FDA under 21 CFR 890.3475."
)

# ---------------------------------------------------------------------------
# Clinical constants — Pediatric Equinus / Toe Walking
# ---------------------------------------------------------------------------
@dataclass
class ToeWalkingPreset:
    name: str
    ankle_dorsiflexion_target_deg: float   # Target DF angle
    plantar_stop_deg: float                # PF stop angle
    afotype: str                           # "solid", "hinged", "posterior_leaf_spring"
    trim_line: str                         # "full", "medial_trim", "lateral_trim"
    thickness_mm: float                    # Wall thickness
    flex_zone: bool                        # Flex zone at ankle
    notes: str = ""

TOE_WALKING_PRESETS: Dict[str, ToeWalkingPreset] = {
    "mild_bilateral": ToeWalkingPreset(
        name="Mild Bilateral Idiopathic Toe Walking",
        ankle_dorsiflexion_target_deg=5.0,
        plantar_stop_deg=0.0,
        afotype="posterior_leaf_spring",
        trim_line="medial_trim",
        thickness_mm=3.0,
        flex_zone=True,
        notes="PLS design with controlled flexibility to encourage heel strike.",
    ),
    "moderate_bilateral": ToeWalkingPreset(
        name="Moderate Bilateral Toe Walking",
        ankle_dorsiflexion_target_deg=0.0,
        plantar_stop_deg=-5.0,
        afotype="hinged",
        trim_line="full",
        thickness_mm=3.5,
        flex_zone=False,
        notes="Hinged AFO with dorsiflexion assist and plantar flexion stop.",
    ),
    "severe_equinus": ToeWalkingPreset(
        name="Severe / Fixed Equinus",
        ankle_dorsiflexion_target_deg=-5.0,
        plantar_stop_deg=-10.0,
        afotype="solid",
        trim_line="full",
        thickness_mm=4.0,
        flex_zone=False,
        notes="Solid AFO for maximum correction. Requires serial casting consideration.",
    ),
    "unilateral_mild": ToeWalkingPreset(
        name="Unilateral Mild Toe Walking",
        ankle_dorsiflexion_target_deg=5.0,
        plantar_stop_deg=0.0,
        afotype="posterior_leaf_spring",
        trim_line="lateral_trim",
        thickness_mm=2.8,
        flex_zone=True,
        notes="Asymmetric design — contralateral limb does not require bracing.",
    ),
}

# ---------------------------------------------------------------------------
# Material specifications for 3D-printed pediatric AFOs
# ---------------------------------------------------------------------------
@dataclass
class MaterialSpec:
    name: str
    iso_10993_biocompat: bool
    tensile_strength_mpa: float
    flexural_modulus_mpa: float
    elongation_at_break_pct: float
    print_temp_c: int
    bed_temp_c: int
    layer_height_mm: float
    infill_pct: int
    suitable_for_pediatric: bool
    notes: str = ""

MATERIALS: Dict[str, MaterialSpec] = {
    "petg": MaterialSpec(
        name="PETG (Polyethylene Terephthalate Glycol)",
        iso_10993_biocompat=True,
        tensile_strength_mpa=50.0,
        flexural_modulus_mpa=2100.0,
        elongation_at_break_pct=23.0,
        print_temp_c=240,
        bed_temp_c=80,
        layer_height_mm=0.2,
        infill_pct=80,
        suitable_for_pediatric=True,
        notes="Most common for pediatric AFOs. Good chemical resistance.",
    ),
    "nylon_pa12": MaterialSpec(
        name="Nylon PA12 (SLS)",
        iso_10993_biocompat=True,
        tensile_strength_mpa=48.0,
        flexural_modulus_mpa=1700.0,
        elongation_at_break_pct=18.0,
        print_temp_c=0,  # SLS, not FDM
        bed_temp_c=0,
        layer_height_mm=0.1,
        infill_pct=100,
        suitable_for_pediatric=True,
        notes="SLS process. Superior fatigue life. Preferred for hinged AFOs.",
    ),
    "tpu_95a": MaterialSpec(
        name="TPU 95A (Flexible)",
        iso_10993_biocompat=True,
        tensile_strength_mpa=40.0,
        flexural_modulus_mpa=80.0,
        elongation_at_break_pct=580.0,
        print_temp_c=225,
        bed_temp_c=60,
        layer_height_mm=0.2,
        infill_pct=100,
        suitable_for_pediatric=True,
        notes="Liner/padding layers only. Not structural.",
    ),
    "ti6al4v_lattice": MaterialSpec(
        name="Ti-6Al-4V (Titanium Lattice Reinforcement)",
        iso_10993_biocompat=True,
        tensile_strength_mpa=900.0,
        flexural_modulus_mpa=114000.0,
        elongation_at_break_pct=14.0,
        print_temp_c=0,  # DMLS/EBM
        bed_temp_c=0,
        layer_height_mm=0.03,
        infill_pct=100,
        suitable_for_pediatric=True,
        notes="DMLS lattice inserts for severe equinus reinforcement ribs only.",
    ),
}

# ---------------------------------------------------------------------------
# Pediatric anthropometric reference ranges (ages 2-12)
# ---------------------------------------------------------------------------
PEDIATRIC_ANTHRO = {
    # age: (foot_length_mm_min, foot_length_mm_max, ankle_width_mm_min, ankle_width_mm_max)
    2: (125, 145, 38, 44),
    3: (135, 160, 40, 47),
    4: (145, 175, 42, 50),
    5: (155, 185, 44, 53),
    6: (165, 200, 46, 55),
    7: (175, 215, 48, 58),
    8: (185, 225, 50, 60),
    9: (195, 240, 52, 63),
    10: (205, 250, 54, 65),
    11: (215, 260, 56, 67),
    12: (225, 275, 58, 70),
}

# ---------------------------------------------------------------------------
# FEA default parameters for pediatric loading
# ---------------------------------------------------------------------------
@dataclass
class FEADefaults:
    safety_factor: float = 3.0          # Pediatric devices require SF ≥ 3.0
    body_weight_multiplier: float = 1.5  # Dynamic gait load = 1.5x BW
    cycle_target: int = 1_000_000        # Fatigue life target cycles
    mesh_refinement: str = "fine"
    max_von_mises_pct: float = 60.0      # Max allowable % of yield strength

FEA_DEFAULTS = FEADefaults()

# ---------------------------------------------------------------------------
# Agent subprocess timeouts (seconds)
# ---------------------------------------------------------------------------
OPENSCAD_TIMEOUT_SEC = 120
BUILD123D_TIMEOUT_SEC = 180
OCTOPRINT_CONNECT_TIMEOUT_SEC = 5

# ---------------------------------------------------------------------------
# AFO geometry validation bounds (millimetres)
# ---------------------------------------------------------------------------
AFO_LENGTH_MIN_MM = 100
AFO_LENGTH_MAX_MM = 400
AFO_HEIGHT_MIN_MM = 80
AFO_HEIGHT_MAX_MM = 350

# ---------------------------------------------------------------------------
# OctoPrint connection settings
# ---------------------------------------------------------------------------
OCTOPRINT_URL = "http://localhost:5000"   # Override with OCTOPRINT_URL env var
OCTOPRINT_API_KEY = ""                    # Override with OCTOPRINT_API_KEY env var

# ---------------------------------------------------------------------------
# Agent orchestration settings
# ---------------------------------------------------------------------------
MAX_AGENT_ITERATIONS = 10
VLM_CRITIQUE_MAX_ROUNDS = 5
HUMAN_REVIEW_REQUIRED = True           # NEVER set False in production
PREFERRED_CAD_ENGINE = "build123d"     # "build123d" | "openscad" | "chat_to_stl"
LOCAL_LLM_MODEL = "llama3.2"           # Assumed local via Ollama or similar
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Sentence-transformers for RAG
