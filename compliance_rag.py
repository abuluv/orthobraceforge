"""
OrthoBraceForge — Compliance RAG Engine
Domain-specific Retrieval-Augmented Generation for:
  - FDA 21 CFR 890.3475 (Limb Orthosis regulatory pathway)
  - ISO 13485:2016 (QMS for medical devices)
  - ISO 10993 (Biocompatibility for pediatric skin-contact devices)
  - Clinical best practices for pediatric AFO design
  - Material safety data for 3D-printed orthoses

All knowledge is embedded locally — no internet required post-install.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import APP_CLASSIFICATION, RAG_DATA_DIR


# ---------------------------------------------------------------------------
# Knowledge Base Document Types
# ---------------------------------------------------------------------------
@dataclass
class RAGDocument:
    doc_id: str
    source: str           # "fda", "iso13485", "iso10993", "clinical", "material"
    title: str
    content: str
    section: str
    keywords: List[str]
    severity: str         # "critical", "major", "minor", "informational"
    embedding: Optional[np.ndarray] = None


@dataclass
class RAGResult:
    document: RAGDocument
    relevance_score: float
    regulatory_flag: bool      # True if this triggers a mandatory review gate
    action_required: str       # "block", "warn", "info"


# ---------------------------------------------------------------------------
# Embedded Knowledge Bases (loaded from bundled JSON)
# ---------------------------------------------------------------------------
class ComplianceKnowledgeBase:
    """Loads and indexes all regulatory/clinical knowledge from bundled JSON files."""

    KNOWLEDGE_FILES = {
        "fda_510k_afo.json": "fda",
        "iso13485_checklist.json": "iso13485",
        "biocompat_pediatric.json": "iso10993",
        "equinus_clinical.json": "clinical",
        "material_specs.json": "material",
    }

    def __init__(self):
        self.documents: List[RAGDocument] = []
        self._embeddings_matrix: Optional[np.ndarray] = None
        self._load_knowledge_bases()
        self._build_index()

    def _load_knowledge_bases(self):
        """Load all JSON knowledge files into RAGDocument instances."""
        for filename, source_type in self.KNOWLEDGE_FILES.items():
            filepath = RAG_DATA_DIR / filename
            if not filepath.exists():
                # Generate default knowledge base if files don't exist yet
                self._generate_default_kb(filepath, source_type)
            with open(filepath, "r", encoding="utf-8") as f:
                entries = json.load(f)
            for entry in entries:
                doc = RAGDocument(
                    doc_id=entry.get("id", f"{source_type}_{len(self.documents)}"),
                    source=source_type,
                    title=entry.get("title", ""),
                    content=entry.get("content", ""),
                    section=entry.get("section", ""),
                    keywords=entry.get("keywords", []),
                    severity=entry.get("severity", "informational"),
                )
                self.documents.append(doc)

    def _build_index(self):
        """Build TF-IDF-style keyword index for local retrieval (no ML model needed)."""
        self._keyword_index: Dict[str, List[int]] = {}
        for idx, doc in enumerate(self.documents):
            tokens = set()
            tokens.update(w.lower() for w in doc.keywords)
            tokens.update(w.lower() for w in doc.title.split())
            tokens.update(w.lower() for w in doc.content.split())
            for token in tokens:
                if len(token) > 2:
                    self._keyword_index.setdefault(token, []).append(idx)

    def _generate_default_kb(self, filepath: Path, source_type: str):
        """Generate default knowledge base entries for the given source type."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        default_entries = self._get_default_entries(source_type)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default_entries, f, indent=2)

    @staticmethod
    def _get_default_entries(source_type: str) -> List[Dict]:
        """Return built-in knowledge entries for each regulatory domain."""
        if source_type == "fda":
            return [
                {
                    "id": "fda_001",
                    "title": "21 CFR 890.3475 — Limb Orthosis Classification",
                    "content": (
                        "Ankle-foot orthoses (AFOs) are classified as Class I or Class II "
                        "medical devices under 21 CFR 890.3475. Custom 3D-printed AFOs for "
                        "pediatric use typically require 510(k) clearance as Class II devices. "
                        "Predicate devices include traditionally manufactured polypropylene AFOs. "
                        "The device must demonstrate substantial equivalence in intended use, "
                        "technological characteristics, and performance."
                    ),
                    "section": "Device Classification",
                    "keywords": ["fda", "510k", "class_ii", "afo", "orthosis", "clearance"],
                    "severity": "critical",
                },
                {
                    "id": "fda_002",
                    "title": "Pediatric-Specific FDA Requirements",
                    "content": (
                        "Pediatric medical devices must comply with the Pediatric Medical Device "
                        "Safety and Improvement Act. For AFOs in children ages 2-12: growth "
                        "accommodation must be documented, materials must meet ISO 10993 for "
                        "prolonged skin contact in pediatric populations, and mechanical testing "
                        "must use pediatric-appropriate loading profiles (typically 1.5x body "
                        "weight dynamic loading with safety factor >= 3.0)."
                    ),
                    "section": "Pediatric Requirements",
                    "keywords": ["pediatric", "children", "growth", "safety_factor", "loading"],
                    "severity": "critical",
                },
                {
                    "id": "fda_003",
                    "title": "3D-Printed Device Technical Considerations",
                    "content": (
                        "FDA guidance 'Technical Considerations for Additive Manufactured Medical "
                        "Devices' (2017) requires: documentation of build orientation effects on "
                        "mechanical properties, post-processing validation (annealing, surface "
                        "finishing), layer adhesion strength testing, dimensional accuracy "
                        "verification (±0.5mm for AFOs), and biocompatibility of the final "
                        "finished device including any support material residue."
                    ),
                    "section": "Additive Manufacturing",
                    "keywords": ["3d_print", "additive", "build_orientation", "layer_adhesion"],
                    "severity": "critical",
                },
                {
                    "id": "fda_004",
                    "title": "Design Controls — 21 CFR 820.30",
                    "content": (
                        "All medical device design activities must follow design controls: "
                        "design input (patient measurements, clinical requirements), design "
                        "output (CAD files, STL, manufacturing instructions), design review "
                        "(human clinician approval gate), design verification (FEA, dimensional "
                        "check), design validation (fit testing on patient), and design transfer "
                        "(print parameters, QC checklist). All records must be maintained."
                    ),
                    "section": "Design Controls",
                    "keywords": ["design_controls", "verification", "validation", "qms"],
                    "severity": "critical",
                },
            ]
        elif source_type == "iso13485":
            return [
                {
                    "id": "iso_001",
                    "title": "ISO 13485:2016 §7.3 — Design and Development",
                    "content": (
                        "Design and development planning shall include: design stages, review/"
                        "verification/validation activities at each stage, responsibilities, "
                        "and methods to ensure traceability. For software-generated medical "
                        "device designs, IEC 62304 software lifecycle processes apply."
                    ),
                    "section": "Design and Development",
                    "keywords": ["iso13485", "design", "development", "planning", "iec62304"],
                    "severity": "critical",
                },
                {
                    "id": "iso_002",
                    "title": "ISO 13485:2016 §4.2.5 — Control of Records",
                    "content": (
                        "Records shall be maintained to provide evidence of conformity. For "
                        "CAD-generated AFOs: complete parameter history, agent decision logs, "
                        "all iteration snapshots, human review decisions with timestamps, "
                        "and file integrity hashes (SHA-256) for all exported STL/STEP files."
                    ),
                    "section": "Document Control",
                    "keywords": ["records", "traceability", "audit", "hash", "document_control"],
                    "severity": "major",
                },
                {
                    "id": "iso_003",
                    "title": "ISO 13485:2016 §8.2.1 — Feedback and Complaints",
                    "content": (
                        "Post-market surveillance processes must capture: device fit issues, "
                        "skin reactions, mechanical failures, patient complaints. For pediatric "
                        "AFOs, 30-day follow-up assessments are recommended to capture growth-"
                        "related fit issues and gait improvement metrics."
                    ),
                    "section": "Post-Market Surveillance",
                    "keywords": ["feedback", "complaints", "surveillance", "follow_up"],
                    "severity": "major",
                },
            ]
        elif source_type == "iso10993":
            return [
                {
                    "id": "bio_001",
                    "title": "ISO 10993-1 — Biological Evaluation of Medical Devices",
                    "content": (
                        "AFOs are surface-contacting devices with prolonged skin exposure (>30 "
                        "days). Required biocompatibility tests for pediatric use: cytotoxicity "
                        "(ISO 10993-5), sensitization (ISO 10993-10), irritation (ISO 10993-10), "
                        "and material characterization (ISO 10993-18). Pediatric skin is more "
                        "permeable and sensitive — additional irritation margins are required."
                    ),
                    "section": "Biocompatibility",
                    "keywords": ["biocompatibility", "skin_contact", "cytotoxicity", "pediatric"],
                    "severity": "critical",
                },
                {
                    "id": "bio_002",
                    "title": "3D-Printed Material Biocompatibility",
                    "content": (
                        "Post-printing biocompatibility depends on: residual monomer content, "
                        "surface roughness (Ra < 12.5 µm for skin contact), extractables/"
                        "leachables from layer interfaces, and support material removal "
                        "completeness. PETG and PA12 are generally recognized as biocompatible "
                        "for skin-contact orthoses when properly processed."
                    ),
                    "section": "Material Processing",
                    "keywords": ["3d_print", "surface_roughness", "extractables", "petg", "pa12"],
                    "severity": "major",
                },
            ]
        elif source_type == "clinical":
            return [
                {
                    "id": "clin_001",
                    "title": "Idiopathic Toe Walking — Clinical Parameters",
                    "content": (
                        "Idiopathic toe walking (ITW) is defined as persistent toe-toe gait "
                        "pattern beyond age 3 without neurological, orthopedic, or developmental "
                        "cause. Prevalence: 5-12% of children. Classification: mild (occasional, "
                        "can heel-walk on command, DF ≥ 5°), moderate (frequent, limited heel-"
                        "walk, DF 0-5°), severe/fixed equinus (constant, unable to heel-walk, "
                        "DF < 0°). AFO management is first-line for moderate-severe ITW."
                    ),
                    "section": "Diagnosis",
                    "keywords": ["toe_walking", "equinus", "idiopathic", "classification", "afo"],
                    "severity": "informational",
                },
                {
                    "id": "clin_002",
                    "title": "AFO Design Principles for Toe Walking Correction",
                    "content": (
                        "AFO design goals for ITW correction: 1) Maintain ankle in neutral-to-"
                        "slight-dorsiflexion during stance, 2) Prevent forefoot-first contact "
                        "at initial contact, 3) Allow controlled plantarflexion if hinged design, "
                        "4) Accommodate growth (recommend 6-month replacement cycle for ages 2-6, "
                        "12-month for ages 7-12), 5) Trim lines must clear malleoli by ≥ 3mm, "
                        "6) Posterior wall must extend to fibular head minus 15mm for lever arm."
                    ),
                    "section": "AFO Design",
                    "keywords": ["afo_design", "dorsiflexion", "trim_line", "correction", "lever_arm"],
                    "severity": "critical",
                },
                {
                    "id": "clin_003",
                    "title": "Pediatric AFO Dimensional Tolerances",
                    "content": (
                        "Critical dimensions for pediatric AFOs: ankle angle ±1°, foot length "
                        "±1.5mm, ankle width ±1.0mm, posterior wall height ±2.0mm, trim line "
                        "clearance minimum 3mm from bony prominences. Wall thickness uniformity "
                        "±0.3mm. These tolerances must be verified before human approval gate."
                    ),
                    "section": "Dimensional Requirements",
                    "keywords": ["tolerances", "dimensions", "ankle_angle", "wall_thickness"],
                    "severity": "critical",
                },
            ]
        else:  # material
            return [
                {
                    "id": "mat_001",
                    "title": "PETG for Pediatric AFOs",
                    "content": (
                        "PETG (Polyethylene Terephthalate Glycol-modified) is the most widely "
                        "used FDM material for 3D-printed pediatric AFOs. Properties: tensile "
                        "strength 50 MPa, flexural modulus 2100 MPa, elongation at break 23%. "
                        "Print parameters: 240°C nozzle, 80°C bed, 0.2mm layer height, 80% "
                        "infill for structural regions, 100% infill for ankle hinge zones."
                    ),
                    "section": "FDM Materials",
                    "keywords": ["petg", "fdm", "print_parameters", "mechanical_properties"],
                    "severity": "informational",
                },
                {
                    "id": "mat_002",
                    "title": "Titanium Lattice Reinforcement for Severe Equinus",
                    "content": (
                        "Ti-6Al-4V DMLS lattice inserts may be used as reinforcement ribs in "
                        "severe equinus AFOs where polymer-only construction is insufficient. "
                        "BCC lattice structure with 60% relative density provides optimal "
                        "stiffness-to-weight ratio. Insert must be bonded with medical-grade "
                        "epoxy (ISO 10993 certified) and edges fully encapsulated in polymer."
                    ),
                    "section": "Metal Reinforcement",
                    "keywords": ["titanium", "lattice", "dmls", "reinforcement", "severe_equinus"],
                    "severity": "major",
                },
            ]


class ComplianceRAG:
    """
    Retrieval-Augmented Generation engine for regulatory compliance.
    Performs keyword-based retrieval with severity-weighted ranking.
    Runs entirely locally with no ML model dependency for basic operation.
    """

    def __init__(self):
        self.kb = ComplianceKnowledgeBase()
        self._severity_weights = {
            "critical": 4.0,
            "major": 2.5,
            "minor": 1.5,
            "informational": 1.0,
        }

    def query(self, query_text: str, top_k: int = 5,
              source_filter: Optional[str] = None) -> List[RAGResult]:
        """
        Retrieve most relevant compliance documents for a given query.

        Args:
            query_text: Natural language or keyword query
            top_k: Number of results to return
            source_filter: Optional filter by source type ("fda", "iso13485", etc.)

        Returns:
            List of RAGResult sorted by relevance score descending
        """
        query_tokens = set(w.lower() for w in query_text.split() if len(w) > 2)
        scored: List[Tuple[int, float]] = []

        for idx, doc in enumerate(self.kb.documents):
            if source_filter and doc.source != source_filter:
                continue
            # Compute keyword overlap score
            doc_tokens = set(w.lower() for w in doc.keywords)
            doc_tokens.update(w.lower() for w in doc.title.split())
            overlap: float = len(query_tokens & doc_tokens)
            if overlap == 0:
                # Check content for partial matches
                content_lower = doc.content.lower()
                overlap = float(sum(1 for t in query_tokens if t in content_lower)) * 0.5
            if overlap > 0:
                severity_weight = self._severity_weights.get(doc.severity, 1.0)
                score = overlap * severity_weight
                scored.append((idx, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in scored[:top_k]:
            doc = self.kb.documents[idx]
            regulatory_flag = doc.severity in ("critical", "major")
            action = "block" if doc.severity == "critical" else (
                "warn" if doc.severity == "major" else "info"
            )
            results.append(RAGResult(
                document=doc,
                relevance_score=score,
                regulatory_flag=regulatory_flag,
                action_required=action,
            ))
        return results

    def check_design_compliance(self, parameters: Dict) -> Dict:
        """
        Run comprehensive compliance check on a set of design parameters.

        Returns dict with:
          - passed: bool
          - flags: list of regulatory flags
          - blocking_issues: list of issues that must be resolved
          - warnings: list of advisory warnings
          - recommendations: list of improvement suggestions
        """
        flags = []
        blocking = []
        warnings = []
        recommendations = []

        # Check wall thickness
        thickness = parameters.get("thickness_mm", 0)
        if thickness < 2.5:
            blocking.append(
                f"Wall thickness {thickness}mm is below minimum 2.5mm for "
                f"pediatric AFO structural integrity (FDA guidance)."
            )
            flags.append("THICKNESS_BELOW_MIN")
        elif thickness < 3.0:
            warnings.append(
                f"Wall thickness {thickness}mm is marginal. Consider ≥3.0mm "
                f"for patients >20kg body weight."
            )

        # Check ankle angle
        ankle_angle = parameters.get("ankle_dorsiflexion_target_deg", None)
        if ankle_angle is not None and ankle_angle < -15:
            blocking.append(
                f"Ankle angle {ankle_angle}° exceeds maximum plantarflexion "
                f"correction range. Risk of pressure injury."
            )
            flags.append("ANGLE_OUT_OF_RANGE")

        # Check patient age
        age = parameters.get("age_years", 0)
        if age < 2:
            blocking.append(
                "Patient age <2 years. AFO intervention for toe walking is "
                "not indicated before age 2 (physiological toe walking is normal)."
            )
            flags.append("AGE_CONTRAINDICATED")
        elif age > 12:
            warnings.append(
                "Patient age >12 years. Skeletal maturity may affect AFO "
                "efficacy. Consider referral to adult orthotics."
            )

        # Check material biocompatibility
        material = parameters.get("material", "")
        if material and material not in ("petg", "nylon_pa12", "tpu_95a", "ti6al4v_lattice"):
            blocking.append(
                f"Material '{material}' is not in the validated biocompatible "
                f"materials list for pediatric skin-contact devices."
            )
            flags.append("MATERIAL_NOT_VALIDATED")

        # Check safety factor
        safety_factor = parameters.get("safety_factor", 3.0)
        if safety_factor < 3.0:
            blocking.append(
                f"Safety factor {safety_factor} is below required minimum "
                f"of 3.0 for pediatric orthotic devices."
            )
            flags.append("SAFETY_FACTOR_LOW")

        # Always flag that human review is required
        flags.append("HUMAN_REVIEW_MANDATORY")
        recommendations.append(
            "All designs must be reviewed and approved by a licensed orthotist "
            "or physician before manufacturing and patient use."
        )

        passed = len(blocking) == 0
        return {
            "passed": passed,
            "flags": flags,
            "blocking_issues": blocking,
            "warnings": warnings,
            "recommendations": recommendations,
            "classification": APP_CLASSIFICATION,
        }

    def get_design_constraints(self, preset_key: str, age: int,
                                weight_kg: float) -> Dict:
        """
        Generate design constraints based on clinical parameters and
        regulatory requirements.
        """
        from config import FEA_DEFAULTS, PEDIATRIC_ANTHRO, TOE_WALKING_PRESETS

        preset = TOE_WALKING_PRESETS.get(preset_key)
        if not preset:
            return {"error": f"Unknown preset: {preset_key}"}

        anthro = PEDIATRIC_ANTHRO.get(age) or PEDIATRIC_ANTHRO.get(6) or (165, 200, 46, 58)

        dynamic_load_n = weight_kg * 9.81 * FEA_DEFAULTS.body_weight_multiplier

        return {
            "preset": preset.name,
            "afo_type": preset.afotype,
            "ankle_target_deg": preset.ankle_dorsiflexion_target_deg,
            "plantar_stop_deg": preset.plantar_stop_deg,
            "wall_thickness_mm": preset.thickness_mm,
            "trim_line": preset.trim_line,
            "flex_zone": preset.flex_zone,
            "foot_length_range_mm": (anthro[0], anthro[1]),
            "ankle_width_range_mm": (anthro[2], anthro[3]),
            "dynamic_load_n": round(dynamic_load_n, 1),
            "safety_factor": FEA_DEFAULTS.safety_factor,
            "max_von_mises_pct": FEA_DEFAULTS.max_von_mises_pct,
            "fatigue_cycles": FEA_DEFAULTS.cycle_target,
            "material_recommendation": "petg" if weight_kg < 30 else "nylon_pa12",
            "growth_accommodation_mm": 5.0 if age < 7 else 3.0,
            "replacement_interval_months": 6 if age < 7 else 12,
            "regulatory_classification": APP_CLASSIFICATION,
        }
