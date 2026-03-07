"""
Tests for export.py — AuditPDFGenerator
Covers text-report fallback and PDF generation path (with reportlab mocked).
"""
import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import config
from database import Database, PatientRecord, DesignRecord
from export import AuditPDFGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """Create a temporary Database instance."""
    db_path = tmp_path / "test.db"
    return Database(db_path=db_path)


@pytest.fixture()
def export_dir(tmp_path, monkeypatch):
    """Point config.EXPORT_DIR to a temporary directory."""
    import export as export_module
    exp = tmp_path / "exports"
    exp.mkdir()
    monkeypatch.setattr(config, "EXPORT_DIR", exp)
    monkeypatch.setattr(export_module, "EXPORT_DIR", exp)
    return exp


@pytest.fixture()
def patient_and_design(db):
    """Insert a patient + design and return (patient_id, design_id)."""
    patient_id = str(uuid.uuid4())
    design_id = str(uuid.uuid4())

    db.create_patient(PatientRecord(
        patient_id=patient_id,
        first_name="Test",
        last_name="Patient",
        date_of_birth="2018-06-15",
        age_years=7,
        weight_kg=25.0,
        height_cm=120.0,
        diagnosis="idiopathic_toe_walking",
        laterality="bilateral",
        severity="moderate",
        clinical_notes="Unit test patient",
    ))

    db.create_design(DesignRecord(
        design_id=design_id,
        patient_id=patient_id,
        preset_key="moderate_bilateral",
        parameters_json="{}",
        cad_engine_used="build123d",
    ))

    db.add_audit(patient_id, design_id, "create", "system", "Design created for unit test")
    db.add_audit(patient_id, design_id, "review", "human:dr_smith", "Reviewed and approved")

    return patient_id, design_id


@pytest.fixture()
def sample_state():
    """Return a representative pipeline state dict."""
    return {
        "run_id": str(uuid.uuid4()),
        "patient": {"age": 7, "weight_kg": 25.0, "height_cm": 120.0},
        "laterality": "bilateral",
        "severity": "moderate",
        "compliance_result": {
            "passed": True,
            "blocking_issues": [],
            "warnings": ["Material batch nearing expiry"],
        },
        "constraints": {"ankle_dorsiflexion_target_deg": 0.0, "thickness_mm": 3.5},
        "cad_engine": "build123d",
        "iteration_count": 3,
        "stl_path": "/tmp/brace.stl",
        "fea_result": {
            "passed": True,
            "max_von_mises_mpa": 18.5,
            "von_mises_pct_yield": 37.0,
            "safety_factor": 3.2,
            "required_safety_factor": 3.0,
            "dynamic_load_n": 367.5,
        },
        "lattice_evaluation": {"needs_reinforcement": False},
        "human_approved": True,
        "human_reviewer": "Dr. Smith",
        "review_notes": "Looks good",
        "warnings": ["Minor asymmetry detected"],
        "trace_log": [
            "Step 1: Compliance check passed",
            "Step 2: CAD generation complete",
            "Step 3: FEA analysis passed",
        ],
    }


# ---------------------------------------------------------------------------
# Helper — force the reportlab import inside generate() to raise ImportError
# ---------------------------------------------------------------------------

def _block_reportlab_import(name, *args, **kwargs):
    """Side-effect for builtins.__import__ that blocks reportlab."""
    if name.startswith("reportlab"):
        raise ImportError("reportlab not installed (mocked)")
    return original_import(name, *args, **kwargs)


original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__


# ---------------------------------------------------------------------------
# Tests — text report fallback
# ---------------------------------------------------------------------------

class TestTextReportGeneration:
    """Tests for _generate_text_report (the ImportError fallback path)."""

    def test_text_report_file_created(self, db, export_dir, patient_and_design, sample_state):
        """Text report is created when reportlab is unavailable."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        assert Path(result_path).exists()
        assert result_path.endswith(".txt")

    def test_text_report_contains_regulatory_banner(self, db, export_dir, patient_and_design, sample_state):
        """Text report must include the regulatory banner."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert config.REGULATORY_BANNER in content

    def test_text_report_contains_patient_id(self, db, export_dir, patient_and_design, sample_state):
        """Text report shows (truncated) patient ID."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert patient_id[:8] in content
        assert "Patient ID:" in content

    def test_text_report_contains_design_id(self, db, export_dir, patient_and_design, sample_state):
        """Text report shows (truncated) design ID."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert design_id[:8] in content
        assert "Design ID:" in content

    def test_text_report_contains_compliance_status(self, db, export_dir, patient_and_design, sample_state):
        """Text report includes compliance pass/fail status."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert "Compliance: PASSED" in content

    def test_text_report_compliance_failed(self, db, export_dir, patient_and_design, sample_state):
        """Text report shows FAILED when compliance did not pass."""
        patient_id, design_id = patient_and_design
        sample_state["compliance_result"]["passed"] = False
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert "Compliance: FAILED" in content

    def test_text_report_contains_fea_status(self, db, export_dir, patient_and_design, sample_state):
        """Text report includes FEA pass/fail status."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert "FEA: PASSED" in content

    def test_text_report_fea_failed(self, db, export_dir, patient_and_design, sample_state):
        """Text report shows FEA FAILED when fea_result.passed is False."""
        patient_id, design_id = patient_and_design
        sample_state["fea_result"]["passed"] = False
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert "FEA: FAILED" in content

    def test_text_report_includes_trace_log(self, db, export_dir, patient_and_design, sample_state):
        """Text report includes all trace log entries."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert "--- Trace Log ---" in content
        for entry in sample_state["trace_log"]:
            assert entry in content

    def test_text_report_includes_human_reviewer(self, db, export_dir, patient_and_design, sample_state):
        """Text report includes human reviewer name."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        content = Path(result_path).read_text(encoding="utf-8")
        assert "Dr. Smith" in content

    def test_text_report_filename_uses_design_id_prefix(self, db, export_dir, patient_and_design, sample_state):
        """Text report filename uses first 8 chars of design_id."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        filename = Path(result_path).name
        assert filename == f"audit_{design_id[:8]}.txt"

    def test_direct_text_report_method(self, db, export_dir, patient_and_design, sample_state):
        """Calling _generate_text_report directly works without mocking imports."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        result_path = gen._generate_text_report(patient_id, design_id, sample_state)

        assert Path(result_path).exists()
        content = Path(result_path).read_text(encoding="utf-8")
        assert "OrthoBraceForge" in content
        assert "Compliance:" in content


# ---------------------------------------------------------------------------
# Tests — PDF generation path (reportlab mocked as available)
# ---------------------------------------------------------------------------

class TestPDFGeneration:
    """Tests for the PDF generation path with reportlab mocked."""

    def test_pdf_path_returned_when_reportlab_available(self, db, export_dir, patient_and_design, sample_state):
        """When reportlab is available, generate() returns a .pdf path and calls doc.build."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        mock_doc = MagicMock()
        mock_simple_doc = MagicMock(return_value=mock_doc)

        mock_reportlab_pagesizes = MagicMock()
        mock_reportlab_pagesizes.letter = (612, 792)
        mock_reportlab_units = MagicMock()
        mock_reportlab_units.inch = 72
        mock_reportlab_styles = MagicMock()
        mock_reportlab_colors = MagicMock()
        mock_reportlab_platypus = MagicMock()
        mock_reportlab_platypus.SimpleDocTemplate = mock_simple_doc

        modules = {
            "reportlab": MagicMock(),
            "reportlab.lib": MagicMock(),
            "reportlab.lib.pagesizes": mock_reportlab_pagesizes,
            "reportlab.lib.units": mock_reportlab_units,
            "reportlab.lib.styles": mock_reportlab_styles,
            "reportlab.lib.colors": mock_reportlab_colors,
            "reportlab.platypus": mock_reportlab_platypus,
        }

        with patch.dict(sys.modules, modules):
            result_path = gen.generate(patient_id, design_id, sample_state)

        assert result_path.endswith(".pdf")
        assert design_id[:8] in result_path
        mock_doc.build.assert_called_once()

    def test_pdf_generation_falls_back_on_import_error(self, db, export_dir, patient_and_design, sample_state):
        """When reportlab import fails, generate() falls back to text report."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        with patch("builtins.__import__", side_effect=_block_reportlab_import):
            result_path = gen.generate(patient_id, design_id, sample_state)

        assert result_path.endswith(".txt")
        assert Path(result_path).exists()


# ---------------------------------------------------------------------------
# Tests — edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_trace_log(self, db, export_dir, patient_and_design, sample_state):
        """Text report handles an empty trace log gracefully."""
        patient_id, design_id = patient_and_design
        sample_state["trace_log"] = []
        gen = AuditPDFGenerator(db)

        result_path = gen._generate_text_report(patient_id, design_id, sample_state)
        content = Path(result_path).read_text(encoding="utf-8")
        assert "--- Trace Log ---" in content

    def test_missing_optional_state_keys(self, db, export_dir, patient_and_design):
        """Text report handles missing optional keys with defaults."""
        patient_id, design_id = patient_and_design
        minimal_state = {"run_id": "abc123"}
        gen = AuditPDFGenerator(db)

        result_path = gen._generate_text_report(patient_id, design_id, minimal_state)
        content = Path(result_path).read_text(encoding="utf-8")
        assert "Engine: N/A" in content
        assert "Compliance: FAILED" in content  # empty dict -> passed is falsy
        assert "FEA: FAILED" in content
        assert "Reviewer: N/A" in content

    def test_text_report_contains_engine_name(self, db, export_dir, patient_and_design, sample_state):
        """Text report includes the CAD engine name."""
        patient_id, design_id = patient_and_design
        gen = AuditPDFGenerator(db)

        result_path = gen._generate_text_report(patient_id, design_id, sample_state)
        content = Path(result_path).read_text(encoding="utf-8")
        assert "Engine: build123d" in content
