"""
OrthoBraceForge — Database Layer
Persistent SQLite for patient cases, design iterations, and audit trail.
ISO 13485 §4.2.5 compliant record keeping.
"""
import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DB_PATH


@dataclass
class PatientRecord:
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str          # ISO 8601
    age_years: int
    weight_kg: float
    height_cm: float
    diagnosis: str              # "idiopathic_toe_walking", etc.
    laterality: str             # "bilateral", "left", "right"
    severity: str               # "mild", "moderate", "severe"
    clinical_notes: str
    gait_video_path: Optional[str] = None
    scan_file_path: Optional[str] = None
    scan_type: Optional[str] = None   # "stl", "obj", "point_cloud"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class DesignRecord:
    design_id: str
    patient_id: str
    preset_key: str
    parameters_json: str         # Full parametric snapshot
    cad_engine_used: str         # "build123d", "openscad", "chat_to_stl"
    stl_path: Optional[str] = None
    step_path: Optional[str] = None
    fea_passed: bool = False
    lattice_validated: bool = False
    vlm_score: float = 0.0
    human_approved: bool = False
    human_reviewer: Optional[str] = None
    review_timestamp: Optional[str] = None
    regulatory_flags: Optional[str] = None
    iteration_count: int = 0
    created_at: Optional[str] = None


@dataclass
class AuditEntry:
    audit_id: str
    patient_id: str
    design_id: Optional[str]
    action: str                  # "create", "modify", "review", "approve", "export", "print"
    actor: str                   # "system", "agent:<name>", "human:<name>"
    details: str
    data_hash: Optional[str] = None   # SHA-256 of associated file
    timestamp: Optional[str] = None


class Database:
    """Thread-safe SQLite database manager with full audit trail."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                age_years INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                height_cm REAL NOT NULL,
                diagnosis TEXT NOT NULL,
                laterality TEXT NOT NULL CHECK(laterality IN ('bilateral','left','right')),
                severity TEXT NOT NULL CHECK(severity IN ('mild','moderate','severe')),
                clinical_notes TEXT DEFAULT '',
                gait_video_path TEXT,
                scan_file_path TEXT,
                scan_type TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS designs (
                design_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL REFERENCES patients(patient_id),
                preset_key TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                cad_engine_used TEXT NOT NULL,
                stl_path TEXT,
                step_path TEXT,
                fea_passed INTEGER DEFAULT 0,
                lattice_validated INTEGER DEFAULT 0,
                vlm_score REAL DEFAULT 0.0,
                human_approved INTEGER DEFAULT 0,
                human_reviewer TEXT,
                review_timestamp TEXT,
                regulatory_flags TEXT,
                iteration_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                audit_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                design_id TEXT,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT NOT NULL,
                data_hash TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_audit_patient ON audit_log(patient_id);
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
            CREATE INDEX IF NOT EXISTS idx_designs_patient ON designs(patient_id);
        """)
        conn.commit()

    # ---------------------------------------------------------------------------
    # Patient CRUD
    # ---------------------------------------------------------------------------
    def create_patient(self, record: PatientRecord) -> str:
        if not record.patient_id:
            record.patient_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record.created_at = now
        record.updated_at = now
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO patients
               (patient_id, first_name, last_name, date_of_birth, age_years,
                weight_kg, height_cm, diagnosis, laterality, severity,
                clinical_notes, gait_video_path, scan_file_path, scan_type,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record.patient_id, record.first_name, record.last_name,
                record.date_of_birth, record.age_years, record.weight_kg,
                record.height_cm, record.diagnosis, record.laterality,
                record.severity, record.clinical_notes, record.gait_video_path,
                record.scan_file_path, record.scan_type,
                record.created_at, record.updated_at,
            ),
        )
        conn.commit()
        self.add_audit(record.patient_id, None, "create", "system",
                       f"Patient record created: {record.first_name} {record.last_name}")
        return record.patient_id

    def get_patient(self, patient_id: str) -> Optional[PatientRecord]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM patients WHERE patient_id=?", (patient_id,)
        ).fetchone()
        if row is None:
            return None
        return PatientRecord(**dict(row))

    def list_patients(self) -> List[PatientRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM patients ORDER BY updated_at DESC"
        ).fetchall()
        return [PatientRecord(**dict(r)) for r in rows]

    # ---------------------------------------------------------------------------
    # Design CRUD
    # ---------------------------------------------------------------------------
    def create_design(self, record: DesignRecord) -> str:
        if not record.design_id:
            record.design_id = str(uuid.uuid4())
        record.created_at = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO designs
               (design_id, patient_id, preset_key, parameters_json,
                cad_engine_used, stl_path, step_path, fea_passed,
                lattice_validated, vlm_score, human_approved, human_reviewer,
                review_timestamp, regulatory_flags, iteration_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record.design_id, record.patient_id, record.preset_key,
                record.parameters_json, record.cad_engine_used, record.stl_path,
                record.step_path, int(record.fea_passed),
                int(record.lattice_validated), record.vlm_score,
                int(record.human_approved), record.human_reviewer,
                record.review_timestamp, record.regulatory_flags,
                record.iteration_count, record.created_at,
            ),
        )
        conn.commit()
        self.add_audit(record.patient_id, record.design_id, "create", "system",
                       f"Design created: engine={record.cad_engine_used}, preset={record.preset_key}")
        return record.design_id

    def update_design(self, design_id: str, updates: Dict[str, Any]):
        conn = self._get_conn()
        set_clauses = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [design_id]
        conn.execute(f"UPDATE designs SET {set_clauses} WHERE design_id=?", values)
        conn.commit()

    def get_design(self, design_id: str) -> Optional[DesignRecord]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM designs WHERE design_id=?", (design_id,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["fea_passed"] = bool(d["fea_passed"])
        d["lattice_validated"] = bool(d["lattice_validated"])
        d["human_approved"] = bool(d["human_approved"])
        return DesignRecord(**d)

    def list_designs_for_patient(self, patient_id: str) -> List[DesignRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM designs WHERE patient_id=? ORDER BY created_at DESC",
            (patient_id,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["fea_passed"] = bool(d["fea_passed"])
            d["lattice_validated"] = bool(d["lattice_validated"])
            d["human_approved"] = bool(d["human_approved"])
            results.append(DesignRecord(**d))
        return results

    # ---------------------------------------------------------------------------
    # Audit Trail
    # ---------------------------------------------------------------------------
    def add_audit(self, patient_id: str, design_id: Optional[str],
                  action: str, actor: str, details: str,
                  file_path: Optional[str] = None):
        audit_id = str(uuid.uuid4())
        data_hash = None
        if file_path and Path(file_path).exists():
            data_hash = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO audit_log
               (audit_id, patient_id, design_id, action, actor, details, data_hash)
               VALUES (?,?,?,?,?,?,?)""",
            (audit_id, patient_id, design_id, action, actor, details, data_hash),
        )
        conn.commit()

    def get_audit_trail(self, patient_id: str) -> List[AuditEntry]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE patient_id=? ORDER BY timestamp ASC",
            (patient_id,),
        ).fetchall()
        return [AuditEntry(**dict(r)) for r in rows]

    def get_full_audit(self) -> List[AuditEntry]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 1000"
        ).fetchall()
        return [AuditEntry(**dict(r)) for r in rows]

    # ---------------------------------------------------------------------------
    # Utility
    # ---------------------------------------------------------------------------
    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
