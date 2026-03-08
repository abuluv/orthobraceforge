"""
Shared pytest fixtures for OrthoBraceForge test suite.
"""
import json

import pytest

from database import Database, DesignRecord, PatientRecord


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite database that is discarded after each test."""
    db_path = tmp_path / "test_orthobraceforge.db"
    db = Database(db_path=db_path)
    yield db
    db.close()


@pytest.fixture
def sample_patient_data():
    """Return a dict of realistic pediatric patient data for testing."""
    return {
        "patient_id": "PAT-TEST-0001",
        "first_name": "Amelia",
        "last_name": "Torres",
        "date_of_birth": "2018-06-15",
        "age_years": 7,
        "weight_kg": 23.5,
        "height_cm": 122.0,
        "diagnosis": "idiopathic_toe_walking",
        "laterality": "bilateral",
        "severity": "moderate",
        "clinical_notes": (
            "Persistent bilateral toe walking since onset of ambulation. "
            "Passive dorsiflexion limited to -5 degrees bilaterally. "
            "No underlying neurological findings on exam."
        ),
        "gait_video_path": "/data/gait/amelia_torres_gait_2025.mp4",
        "scan_file_path": "/data/scans/amelia_torres_feet.stl",
        "scan_type": "stl",
    }


@pytest.fixture
def sample_patient_record(sample_patient_data):
    """Return a PatientRecord dataclass instance built from sample data."""
    return PatientRecord(**sample_patient_data)


@pytest.fixture
def sample_design_record():
    """Return a DesignRecord dataclass instance with realistic AFO design data."""
    parameters = {
        "ankle_dorsiflexion_target_deg": 0.0,
        "plantar_stop_deg": -5.0,
        "afotype": "hinged",
        "trim_line": "full",
        "thickness_mm": 3.5,
        "flex_zone": False,
        "foot_length_mm": 190.0,
        "ankle_width_mm": 52.0,
        "material": "petg",
        "infill_pct": 80,
    }
    return DesignRecord(
        design_id="DES-TEST-0001",
        patient_id="PAT-TEST-0001",
        preset_key="moderate_bilateral",
        parameters_json=json.dumps(parameters),
        cad_engine_used="build123d",
        stl_path="/data/exports/DES-TEST-0001.stl",
        step_path="/data/exports/DES-TEST-0001.step",
        fea_passed=True,
        lattice_validated=False,
        vlm_score=7.8,
        human_approved=False,
        human_reviewer=None,
        review_timestamp=None,
        regulatory_flags=None,
        iteration_count=2,
    )


@pytest.fixture
def mock_pipeline_state(sample_patient_data):
    """Return a realistic PipelineState dict representing an in-progress design pipeline."""
    return {
        "patient": sample_patient_data,
        "preset_key": "moderate_bilateral",
        "current_step": "fea_analysis",
        "steps_completed": ["intake", "scan_processing", "parametric_design"],
        "steps_remaining": ["fea_analysis", "vlm_critique", "human_review", "export"],
        "iteration": 2,
        "max_iterations": 10,
        "cad_engine": "build123d",
        "stl_path": "/data/exports/DES-TEST-0001.stl",
        "fea_results": {
            "max_von_mises_mpa": 28.4,
            "safety_factor": 3.2,
            "fatigue_cycles": 1_200_000,
            "passed": True,
        },
        "vlm_score": None,
        "human_approved": False,
        "errors": [],
        "warnings": ["Ankle width near lower bound for age group."],
    }
