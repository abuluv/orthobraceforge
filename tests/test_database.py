"""Unit tests for the OrthoBraceForge database layer."""

import hashlib
import json
import sqlite3

import pytest

from database import Database, DesignRecord, PatientRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_patient(**overrides) -> PatientRecord:
    """Return a PatientRecord with sensible defaults; override any field."""
    defaults = dict(
        patient_id="",
        first_name="Jane",
        last_name="Doe",
        date_of_birth="2018-05-12",
        age_years=7,
        weight_kg=23.0,
        height_cm=120.0,
        diagnosis="idiopathic_toe_walking",
        laterality="bilateral",
        severity="moderate",
        clinical_notes="Initial assessment",
    )
    defaults.update(overrides)
    return PatientRecord(**defaults)


def _make_design(patient_id: str, **overrides) -> DesignRecord:
    """Return a DesignRecord with sensible defaults; override any field."""
    defaults = dict(
        design_id="",
        patient_id=patient_id,
        preset_key="afo_standard",
        parameters_json=json.dumps({"ankle_angle": 90}),
        cad_engine_used="build123d",
    )
    defaults.update(overrides)
    return DesignRecord(**defaults)


@pytest.fixture()
def db(tmp_path):
    """Yield a Database backed by a temporary SQLite file."""
    database = Database(db_path=tmp_path / "test.db")
    yield database
    database.close()


# ---------------------------------------------------------------------------
# 1. Patient CRUD
# ---------------------------------------------------------------------------

class TestPatientCRUD:

    def test_create_patient_returns_id(self, db):
        pid = db.create_patient(_make_patient())
        assert pid
        assert isinstance(pid, str)

    def test_create_patient_auto_generates_id_when_empty(self, db):
        pid = db.create_patient(_make_patient(patient_id=""))
        assert len(pid) == 36  # UUID4 length

    def test_create_patient_uses_provided_id(self, db):
        pid = db.create_patient(_make_patient(patient_id="CUSTOM-001"))
        assert pid == "CUSTOM-001"

    def test_get_patient_returns_record(self, db):
        pid = db.create_patient(_make_patient(first_name="Alice", last_name="Smith"))
        patient = db.get_patient(pid)
        assert patient is not None
        assert patient.first_name == "Alice"
        assert patient.last_name == "Smith"
        assert patient.laterality == "bilateral"
        assert patient.severity == "moderate"

    def test_get_patient_nonexistent_returns_none(self, db):
        assert db.get_patient("no-such-id") is None

    def test_list_patients_empty(self, db):
        assert db.list_patients() == []

    def test_list_patients_returns_all(self, db):
        db.create_patient(_make_patient(first_name="A"))
        db.create_patient(_make_patient(first_name="B"))
        db.create_patient(_make_patient(first_name="C"))
        patients = db.list_patients()
        assert len(patients) == 3

    def test_create_patient_sets_timestamps(self, db):
        pid = db.create_patient(_make_patient())
        patient = db.get_patient(pid)
        assert patient.created_at is not None
        assert patient.updated_at is not None


# ---------------------------------------------------------------------------
# 2. Design CRUD
# ---------------------------------------------------------------------------

class TestDesignCRUD:

    def test_create_design_returns_id(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid))
        assert did
        assert isinstance(did, str)

    def test_create_design_auto_generates_id(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid, design_id=""))
        assert len(did) == 36

    def test_create_design_uses_provided_id(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid, design_id="DES-001"))
        assert did == "DES-001"

    def test_get_design_returns_record(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid, preset_key="afo_sport"))
        design = db.get_design(did)
        assert design is not None
        assert design.preset_key == "afo_sport"
        assert design.patient_id == pid
        assert design.cad_engine_used == "build123d"

    def test_get_design_nonexistent_returns_none(self, db):
        assert db.get_design("no-such-design") is None

    def test_get_design_booleans_are_bool(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid))
        design = db.get_design(did)
        assert isinstance(design.fea_passed, bool)
        assert isinstance(design.lattice_validated, bool)
        assert isinstance(design.human_approved, bool)

    def test_update_design(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid))
        db.update_design(did, {"fea_passed": 1, "vlm_score": 0.95})
        design = db.get_design(did)
        assert design.fea_passed is True
        assert design.vlm_score == pytest.approx(0.95)

    def test_update_design_human_approval(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid))
        db.update_design(did, {
            "human_approved": 1,
            "human_reviewer": "Dr. Jones",
        })
        design = db.get_design(did)
        assert design.human_approved is True
        assert design.human_reviewer == "Dr. Jones"

    def test_list_designs_for_patient_empty(self, db):
        pid = db.create_patient(_make_patient())
        assert db.list_designs_for_patient(pid) == []

    def test_list_designs_for_patient(self, db):
        pid = db.create_patient(_make_patient())
        db.create_design(_make_design(pid, preset_key="preset_a"))
        db.create_design(_make_design(pid, preset_key="preset_b"))
        designs = db.list_designs_for_patient(pid)
        assert len(designs) == 2

    def test_list_designs_for_patient_isolation(self, db):
        pid1 = db.create_patient(_make_patient(first_name="A"))
        pid2 = db.create_patient(_make_patient(first_name="B"))
        db.create_design(_make_design(pid1))
        db.create_design(_make_design(pid2))
        assert len(db.list_designs_for_patient(pid1)) == 1
        assert len(db.list_designs_for_patient(pid2)) == 1

    def test_create_design_sets_timestamp(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid))
        design = db.get_design(did)
        assert design.created_at is not None


# ---------------------------------------------------------------------------
# 3. Audit trail
# ---------------------------------------------------------------------------

class TestAuditTrail:

    def test_add_audit_and_retrieve_by_patient(self, db):
        pid = db.create_patient(_make_patient())
        db.add_audit(pid, None, "review", "human:Dr. Smith", "Reviewed case")
        trail = db.get_audit_trail(pid)
        # create_patient adds one auto-audit, plus the manual one
        manual = [e for e in trail if e.action == "review"]
        assert len(manual) == 1
        assert manual[0].actor == "human:Dr. Smith"
        assert manual[0].details == "Reviewed case"

    def test_get_audit_trail_empty_for_unknown_patient(self, db):
        assert db.get_audit_trail("unknown") == []

    def test_get_full_audit(self, db):
        pid = db.create_patient(_make_patient())
        db.add_audit(pid, None, "export", "system", "Exported STL")
        full = db.get_full_audit()
        assert len(full) >= 2  # create + export

    def test_audit_entry_has_timestamp(self, db):
        pid = db.create_patient(_make_patient())
        trail = db.get_audit_trail(pid)
        assert all(e.timestamp is not None for e in trail)

    def test_audit_entry_has_uuid(self, db):
        pid = db.create_patient(_make_patient())
        trail = db.get_audit_trail(pid)
        assert all(len(e.audit_id) == 36 for e in trail)

    def test_add_audit_with_file_path(self, db, tmp_path):
        content = b"binary stl data"
        f = tmp_path / "model.stl"
        f.write_bytes(content)
        pid = db.create_patient(_make_patient())
        db.add_audit(pid, None, "export", "system", "Exported", file_path=str(f))
        trail = db.get_audit_trail(pid)
        export_entry = [e for e in trail if e.action == "export"][0]
        expected_hash = hashlib.sha256(content).hexdigest()
        assert export_entry.data_hash == expected_hash

    def test_add_audit_with_nonexistent_file_path(self, db):
        pid = db.create_patient(_make_patient())
        db.add_audit(pid, None, "export", "system", "Exported",
                     file_path="/nonexistent/file.stl")
        trail = db.get_audit_trail(pid)
        export_entry = [e for e in trail if e.action == "export"][0]
        assert export_entry.data_hash is None


# ---------------------------------------------------------------------------
# 4. Auto-generated timestamps and IDs
# ---------------------------------------------------------------------------

class TestAutoGeneration:

    def test_patient_id_auto_generated(self, db):
        pid = db.create_patient(_make_patient(patient_id=""))
        assert pid
        assert len(pid) == 36

    def test_design_id_auto_generated(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid, design_id=""))
        assert did
        assert len(did) == 36

    def test_patient_timestamps_populated(self, db):
        pid = db.create_patient(_make_patient())
        p = db.get_patient(pid)
        assert p.created_at is not None
        assert p.updated_at is not None

    def test_design_timestamp_populated(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid))
        d = db.get_design(did)
        assert d.created_at is not None

    def test_audit_timestamp_populated(self, db):
        pid = db.create_patient(_make_patient())
        entries = db.get_audit_trail(pid)
        assert len(entries) >= 1
        assert entries[0].timestamp is not None


# ---------------------------------------------------------------------------
# 5. create_patient auto-generates audit entry
# ---------------------------------------------------------------------------

class TestCreatePatientAudit:

    def test_create_patient_creates_audit_entry(self, db):
        pid = db.create_patient(_make_patient(first_name="Alice", last_name="Wu"))
        trail = db.get_audit_trail(pid)
        assert len(trail) == 1
        entry = trail[0]
        assert entry.action == "create"
        assert entry.actor == "system"
        assert "Alice Wu" in entry.details
        assert entry.patient_id == pid
        assert entry.design_id is None


# ---------------------------------------------------------------------------
# 6. create_design auto-generates audit entry
# ---------------------------------------------------------------------------

class TestCreateDesignAudit:

    def test_create_design_creates_audit_entry(self, db):
        pid = db.create_patient(_make_patient())
        did = db.create_design(_make_design(pid, cad_engine_used="openscad",
                                            preset_key="afo_custom"))
        trail = db.get_audit_trail(pid)
        design_audits = [e for e in trail if e.design_id == did]
        assert len(design_audits) == 1
        entry = design_audits[0]
        assert entry.action == "create"
        assert entry.actor == "system"
        assert "openscad" in entry.details
        assert "afo_custom" in entry.details


# ---------------------------------------------------------------------------
# 7. Foreign key constraint
# ---------------------------------------------------------------------------

class TestForeignKey:

    def test_design_requires_existing_patient(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.create_design(_make_design("nonexistent-patient-id"))


# ---------------------------------------------------------------------------
# 8. CHECK constraints (laterality, severity)
# ---------------------------------------------------------------------------

class TestCheckConstraints:

    @pytest.mark.parametrize("laterality", ["bilateral", "left", "right"])
    def test_valid_laterality(self, db, laterality):
        pid = db.create_patient(_make_patient(laterality=laterality))
        assert db.get_patient(pid).laterality == laterality

    def test_invalid_laterality_rejected(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.create_patient(_make_patient(laterality="upper"))

    @pytest.mark.parametrize("severity", ["mild", "moderate", "severe"])
    def test_valid_severity(self, db, severity):
        pid = db.create_patient(_make_patient(severity=severity))
        assert db.get_patient(pid).severity == severity

    def test_invalid_severity_rejected(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.create_patient(_make_patient(severity="extreme"))


# ---------------------------------------------------------------------------
# 9. File hash computation
# ---------------------------------------------------------------------------

class TestFileHash:

    def test_compute_file_hash(self, tmp_path):
        content = b"OrthoBraceForge test content"
        f = tmp_path / "test_file.bin"
        f.write_bytes(content)
        result = Database.compute_file_hash(str(f))
        expected = hashlib.sha256(content).hexdigest()
        assert result == expected
        assert len(result) == 64  # SHA-256 hex digest length

    def test_compute_file_hash_different_content(self, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert Database.compute_file_hash(str(f1)) != Database.compute_file_hash(str(f2))

    def test_compute_file_hash_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            Database.compute_file_hash("/nonexistent/path.stl")


# ---------------------------------------------------------------------------
# 10. Database close / reopen
# ---------------------------------------------------------------------------

class TestCloseReopen:

    def test_close_sets_conn_to_none(self, tmp_path):
        db = Database(db_path=tmp_path / "test.db")
        db.close()
        assert db._conn is None

    def test_data_persists_after_close_reopen(self, tmp_path):
        db_path = tmp_path / "test.db"
        db1 = Database(db_path=db_path)
        pid = db1.create_patient(_make_patient(first_name="Persist"))
        db1.close()

        db2 = Database(db_path=db_path)
        patient = db2.get_patient(pid)
        assert patient is not None
        assert patient.first_name == "Persist"
        db2.close()

    def test_designs_persist_after_close_reopen(self, tmp_path):
        db_path = tmp_path / "test.db"
        db1 = Database(db_path=db_path)
        pid = db1.create_patient(_make_patient())
        did = db1.create_design(_make_design(pid, preset_key="persist_test"))
        db1.close()

        db2 = Database(db_path=db_path)
        design = db2.get_design(did)
        assert design is not None
        assert design.preset_key == "persist_test"
        db2.close()

    def test_audit_persists_after_close_reopen(self, tmp_path):
        db_path = tmp_path / "test.db"
        db1 = Database(db_path=db_path)
        pid = db1.create_patient(_make_patient())
        db1.add_audit(pid, None, "review", "human:X", "Checked")
        db1.close()

        db2 = Database(db_path=db_path)
        trail = db2.get_audit_trail(pid)
        assert len(trail) == 2  # auto-create + manual
        db2.close()

    def test_double_close_is_safe(self, tmp_path):
        db = Database(db_path=tmp_path / "test.db")
        db.close()
        db.close()  # should not raise
