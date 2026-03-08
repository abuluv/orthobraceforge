"""
OrthoBraceForge — LangGraph Orchestration Engine
Full agentic pipeline from patient input → printable AFO STL.
Embeds all 9 vendored repos as agent nodes in a directed graph.

State machine phases:
  1. INTAKE        → Parse patient data + scan
  2. COMPLIANCE    → RAG check against FDA/ISO/biocompat
  3. PARAMETRIC    → Generate AFO parameters from scan + presets
  4. CAD_GEN       → Generate CAD (build123d preferred → OpenSCAD → fallback)
  5. RENDER        → Headless render for visual inspection
  6. VLM_CRITIQUE  → VLM-based design critique loop
  7. FEA           → Finite element stress analysis
  8. LATTICE       → Ti lattice reinforcement evaluation
  9. HUMAN_REVIEW  → Mandatory human approval gate
  10. EXPORT       → STL/STEP export + audit trail
  11. PRINT        → Optional MCP print queue + monitoring
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from agents import (
    Agentic3DAgent,
    AgenticAlloyAgent,
    CADRenderAgent,
    ChatToSTLAgent,
    FormaAIAgent,
    OctoMCPAgent,
    OrthoInsolesAgent,
    PrintDefectAgent,
    TalkCADAgent,
    VLMCritiqueAgent,
)
from compliance_rag import ComplianceRAG
from config import (
    HUMAN_REVIEW_REQUIRED,
    MAX_AGENT_ITERATIONS,
    PEDIATRIC_ANTHRO,
    PREFERRED_CAD_ENGINE,
    TOE_WALKING_PRESETS,
)
from database import Database, DesignRecord, PatientRecord
from exceptions import OrthoError

logger = logging.getLogger("orthobraceforge.orchestration")


# ===========================================================================
# State Definition
# ===========================================================================
class Phase(str, Enum):
    INTAKE = "intake"
    COMPLIANCE = "compliance"
    PARAMETRIC = "parametric"
    CAD_GEN = "cad_generation"
    RENDER = "render"
    VLM_CRITIQUE = "vlm_critique"
    FEA = "fea_analysis"
    LATTICE = "lattice_eval"
    HUMAN_REVIEW = "human_review"
    EXPORT = "export"
    PRINT = "print"
    COMPLETE = "complete"
    ERROR = "error"


class PipelineState(TypedDict, total=False):
    """Complete state flowing through the orchestration graph."""
    # Identity
    run_id: str
    patient_id: str
    design_id: str
    phase: str

    # Patient data
    patient: Dict[str, Any]
    scan_path: Optional[str]
    measurements: Dict[str, Any]

    # Clinical
    preset_key: str
    severity: str
    laterality: str
    constraints: Dict[str, Any]

    # Compliance
    compliance_result: Dict[str, Any]
    regulatory_flags: List[str]

    # CAD generation
    cad_engine: str
    cad_result: Optional[Dict[str, Any]]
    stl_path: Optional[str]
    step_path: Optional[str]
    build_code: Optional[str]

    # Validation
    render_images: List[str]
    vlm_critique: Dict[str, Any]
    fea_result: Dict[str, Any]
    lattice_evaluation: Dict[str, Any]

    # Human review
    human_approved: bool
    human_reviewer: Optional[str]
    review_notes: Optional[str]

    # Export
    export_paths: List[str]
    audit_pdf_path: Optional[str]

    # Print
    print_queued: bool
    printer_status: Dict[str, Any]

    # Logging
    trace_log: List[str]
    errors: List[str]
    warnings: List[str]
    iteration_count: int


# ===========================================================================
# Orchestrator
# ===========================================================================
class OrchoBraceOrchestrator:
    """
    LangGraph-style orchestrator that routes state through agent nodes.
    Implements the full pipeline as a directed graph with conditional edges.

    Note: Uses a manual graph implementation for PyInstaller compatibility
    (avoids LangGraph's dynamic import issues in frozen executables).
    The API mirrors LangGraph's StateGraph pattern.
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.rag = ComplianceRAG()

        # Instantiate all agents
        self.agents = {
            "forma_ai": FormaAIAgent(),
            "agentic3d": Agentic3DAgent(),
            "talkcad": TalkCADAgent(),
            "cad_render": CADRenderAgent(),
            "vlm_critique": VLMCritiqueAgent(),
            "llm_3d_print": PrintDefectAgent(),
            "ortho_insoles": OrthoInsolesAgent(),
            "octo_mcp": OctoMCPAgent(),
            "agentic_alloy": AgenticAlloyAgent(),
            "chat_to_stl": ChatToSTLAgent(),
        }

        # Callbacks for GUI updates
        self._on_phase_change = None
        self._on_trace_update = None
        self._on_human_review_needed = None
        self._on_error = None

    def set_callbacks(self, on_phase_change=None, on_trace_update=None,
                      on_human_review_needed=None, on_error=None):
        """Register GUI callback functions."""
        self._on_phase_change = on_phase_change
        self._on_trace_update = on_trace_update
        self._on_human_review_needed = on_human_review_needed
        self._on_error = on_error

    def _emit_phase(self, state: PipelineState, phase: Phase):
        state["phase"] = phase.value
        if self._on_phase_change:
            self._on_phase_change(phase.value, state)

    def _emit_trace(self, state: PipelineState, message: str):
        state.setdefault("trace_log", []).append(message)
        logger.info(message)
        if self._on_trace_update:
            self._on_trace_update(message)

    def _emit_error(self, message: str):
        if self._on_error:
            self._on_error(message)

    # ---------------------------------------------------------------------------
    # Main pipeline entry point
    # ---------------------------------------------------------------------------
    def run_pipeline(self, patient_data: Dict, preset_key: str,
                     scan_path: Optional[str] = None,
                     nl_description: str = "",
                     skip_print: bool = True) -> PipelineState:
        """
        Execute the full AFO generation pipeline.

        Args:
            patient_data: Patient demographics and clinical info
            preset_key: Key from TOE_WALKING_PRESETS
            scan_path: Optional path to foot/ankle scan file
            nl_description: Optional NL refinement instructions
            skip_print: If True, stop after export (don't queue print)

        Returns:
            Final PipelineState with all results
        """
        # Initialize state
        state: PipelineState = {
            "run_id": str(uuid.uuid4()),
            "phase": Phase.INTAKE.value,
            "patient": patient_data,
            "preset_key": preset_key,
            "scan_path": scan_path,
            "measurements": {},
            "constraints": {},
            "cad_engine": PREFERRED_CAD_ENGINE,
            "trace_log": [],
            "errors": [],
            "warnings": [],
            "iteration_count": 0,
            "human_approved": False,
            "print_queued": False,
            "render_images": [],
            "export_paths": [],
            "regulatory_flags": [],
        }

        try:
            # Phase 1: Intake
            state = self._node_intake(state)

            # Phase 2: Compliance pre-check
            state = self._node_compliance(state)
            if not state["compliance_result"].get("passed", False):
                blocking = state["compliance_result"].get("blocking_issues", [])
                if blocking:
                    state["errors"].extend(blocking)
                    self._emit_phase(state, Phase.ERROR)
                    return state

            # Phase 3: Parametric prediction from scan
            state = self._node_parametric(state)

            # Phase 4: CAD generation (with fallback chain)
            state = self._node_cad_generation(state)
            if not state.get("stl_path"):
                state["errors"].append("All CAD generation methods failed")
                self._emit_phase(state, Phase.ERROR)
                return state

            # Phase 5: Render
            state = self._node_render(state)

            # Phase 6: VLM critique loop
            state = self._node_vlm_critique(state)

            # Phase 7: FEA analysis
            state = self._node_fea(state)

            # Phase 8: Lattice evaluation
            state = self._node_lattice(state)

            # Phase 9: Human review gate (MANDATORY)
            state = self._node_human_review(state)
            if not state.get("human_approved", False):
                self._emit_trace(state, "⚠ Pipeline paused — awaiting human review")
                return state

            # Phase 10: Export
            state = self._node_export(state)

            # Phase 11: Print (optional)
            if not skip_print:
                state = self._node_print(state)

            self._emit_phase(state, Phase.COMPLETE)
            self._emit_trace(state, "✓ Pipeline completed successfully")

        except OrthoError as e:
            state["errors"].append(f"Pipeline error ({type(e).__name__}): {e}")
            self._emit_phase(state, Phase.ERROR)
            self._emit_error(str(e))
            logger.error("Pipeline domain error", exc_info=True)
        except Exception as e:
            state["errors"].append(f"Unexpected pipeline exception: {str(e)}")
            self._emit_phase(state, Phase.ERROR)
            self._emit_error(str(e))
            logger.exception("Unexpected pipeline error")

        return state

    # ---------------------------------------------------------------------------
    # Pipeline Nodes
    # ---------------------------------------------------------------------------
    def _validate_measurements(self, state: PipelineState) -> None:
        """Cross-validate patient measurements against PEDIATRIC_ANTHRO ranges.

        Adds warnings to state when measurements deviate from age-based norms.
        Does not block the pipeline — warnings only.
        """
        patient = state["patient"]
        age = patient.get("age", 0)
        if age not in PEDIATRIC_ANTHRO:
            return

        fl_min, fl_max, aw_min, aw_max = PEDIATRIC_ANTHRO[age]
        foot_length = patient.get("foot_length_mm")
        ankle_width = patient.get("ankle_width_mm")

        if foot_length is not None:
            if foot_length < fl_min or foot_length > fl_max:
                state["warnings"].append(
                    f"Foot length {foot_length}mm outside expected range "
                    f"[{fl_min}-{fl_max}mm] for age {age}"
                )
                self._emit_trace(
                    state,
                    f"⚠ Foot length {foot_length}mm outside range [{fl_min}-{fl_max}] for age {age}",
                )

        if ankle_width is not None:
            if ankle_width < aw_min or ankle_width > aw_max:
                state["warnings"].append(
                    f"Ankle width {ankle_width}mm outside expected range "
                    f"[{aw_min}-{aw_max}mm] for age {age}"
                )
                self._emit_trace(
                    state,
                    f"⚠ Ankle width {ankle_width}mm outside range [{aw_min}-{aw_max}] for age {age}",
                )

    def _node_intake(self, state: PipelineState) -> PipelineState:
        """Phase 1: Process patient intake data and create DB records."""
        self._emit_phase(state, Phase.INTAKE)
        self._emit_trace(state, "Processing patient intake data")

        patient_data = state["patient"]

        # Cross-validate measurements against age norms
        self._validate_measurements(state)

        # Create patient record
        record = PatientRecord(
            patient_id="",
            first_name=patient_data.get("first_name", ""),
            last_name=patient_data.get("last_name", ""),
            date_of_birth=patient_data.get("dob", ""),
            age_years=patient_data.get("age", 0),
            weight_kg=patient_data.get("weight_kg", 0),
            height_cm=patient_data.get("height_cm", 0),
            diagnosis="idiopathic_toe_walking",
            laterality=patient_data.get("laterality", "bilateral"),
            severity=patient_data.get("severity", "moderate"),
            clinical_notes=patient_data.get("notes", ""),
            scan_file_path=state.get("scan_path"),
            scan_type=patient_data.get("scan_type"),
        )
        patient_id = self.db.create_patient(record)
        state["patient_id"] = patient_id
        state["severity"] = record.severity
        state["laterality"] = record.laterality

        # Create design record
        design_id = str(uuid.uuid4())
        state["design_id"] = design_id

        self._emit_trace(state, f"Patient {patient_id[:8]}… registered, design {design_id[:8]}… created")
        return state

    def _node_compliance(self, state: PipelineState) -> PipelineState:
        """Phase 2: Run compliance checks against RAG knowledge base."""
        self._emit_phase(state, Phase.COMPLIANCE)
        self._emit_trace(state, "Running regulatory compliance pre-check")

        preset = TOE_WALKING_PRESETS.get(state["preset_key"])
        if not preset:
            state["compliance_result"] = {
                "passed": False,
                "blocking_issues": [f"Unknown preset: {state['preset_key']}"],
            }
            return state

        check_params = {
            "age_years": state["patient"].get("age", 0),
            "weight_kg": state["patient"].get("weight_kg", 0),
            "thickness_mm": preset.thickness_mm,
            "ankle_dorsiflexion_target_deg": preset.ankle_dorsiflexion_target_deg,
            "material": "petg",
            "safety_factor": 3.0,
        }

        result = self.rag.check_design_compliance(check_params)
        state["compliance_result"] = result
        state["regulatory_flags"] = result.get("flags", [])

        # Also get design constraints
        constraints = self.rag.get_design_constraints(
            state["preset_key"],
            state["patient"].get("age", 6),
            state["patient"].get("weight_kg", 20),
        )
        state["constraints"] = constraints

        status = "PASSED" if result["passed"] else "BLOCKED"
        self._emit_trace(state, f"Compliance check: {status} | Flags: {result['flags']}")

        # Log warnings
        for warn in result.get("warnings", []):
            state["warnings"].append(warn)
            self._emit_trace(state, f"⚠ Warning: {warn}")

        self.db.add_audit(
            state["patient_id"], state["design_id"],
            "compliance_check", "system",
            f"Compliance {status}: {json.dumps(result['flags'])}",
        )
        return state

    def _node_parametric(self, state: PipelineState) -> PipelineState:
        """Phase 3: Extract/predict AFO parameters from scan data."""
        self._emit_phase(state, Phase.PARAMETRIC)
        self._emit_trace(state, "Generating parametric predictions")

        result = self.agents["ortho_insoles"].run({
            "scan_path": state.get("scan_path", ""),
            "measurements": state.get("measurements", {}),
            "run_id": state["run_id"],
            "patient_id": state["patient_id"],
        })

        if result.success:
            predictions = result.output_data.get("predictions", {})
            measurements = result.output_data.get("measurements", {})
            state["measurements"] = measurements

            # Merge predictions into constraints
            constraints = state.get("constraints", {})
            if predictions.get("recommended_footplate_length"):
                constraints["foot_length_mm"] = predictions["recommended_footplate_length"]
            if predictions.get("recommended_footplate_width"):
                constraints["ankle_width_mm"] = predictions["recommended_footplate_width"] / 1.4
            state["constraints"] = constraints

        state["trace_log"].extend(result.trace_log)
        return state

    def _node_cad_generation(self, state: PipelineState) -> PipelineState:
        """Phase 4: Generate CAD with fallback chain (build123d → OpenSCAD → Chat-To-STL)."""
        self._emit_phase(state, Phase.CAD_GEN)
        self._emit_trace(state, f"Starting CAD generation (engine: {state['cad_engine']})")

        constraints = state.get("constraints", {})
        gen_params = {
            "constraints": constraints,
            "design_id": state["design_id"],
            "description": (
                f"Pediatric AFO for {state['severity']} {state['laterality']} "
                f"idiopathic toe walking, age {state['patient'].get('age', 6)} years"
            ),
            "max_iterations": MAX_AGENT_ITERATIONS,
            "run_id": state["run_id"],
            "patient_id": state["patient_id"],
        }

        # Attempt 1: build123d (preferred)
        if state["cad_engine"] in ("build123d", PREFERRED_CAD_ENGINE):
            self._emit_trace(state, "Attempting build123d generation (FormaAI)")
            result = self.agents["forma_ai"].run(gen_params)
            if result.success and result.output_files:
                state["cad_result"] = result.output_data
                state["stl_path"] = result.output_files[0]
                state["step_path"] = result.output_files[1] if len(result.output_files) > 1 else None
                state["build_code"] = result.output_data.get("build123d_code", "")
                state["cad_engine"] = "build123d"
                state["iteration_count"] = result.iterations_used
                state["trace_log"].extend(result.trace_log)
                self._emit_trace(state, f"✓ build123d succeeded in {result.iterations_used} iterations")
                self._record_design(state)
                return state
            self._emit_trace(state, f"build123d failed: {result.errors}")

        # Attempt 2: OpenSCAD
        self._emit_trace(state, "Falling back to OpenSCAD (Agentic3D)")
        result = self.agents["agentic3d"].run(gen_params)
        if result.success and result.output_files:
            state["cad_result"] = result.output_data
            state["stl_path"] = result.output_files[0]
            state["cad_engine"] = "openscad"
            state["iteration_count"] = result.iterations_used
            state["trace_log"].extend(result.trace_log)
            self._emit_trace(state, f"✓ OpenSCAD succeeded in {result.iterations_used} iterations")
            self._record_design(state)
            return state
        self._emit_trace(state, f"OpenSCAD failed: {result.errors}")

        # Attempt 3: Chat-To-STL fallback
        self._emit_trace(state, "Falling back to Chat-To-STL")
        result = self.agents["chat_to_stl"].run(gen_params)
        if result.success and result.output_files:
            state["cad_result"] = result.output_data
            state["stl_path"] = result.output_files[0]
            state["cad_engine"] = "chat_to_stl"
            state["iteration_count"] = result.iterations_used
            state["warnings"].extend(result.warnings)
            state["trace_log"].extend(result.trace_log)
            self._emit_trace(state, "✓ Fallback STL generated (reduced fidelity)")
            self._record_design(state)
            return state

        # All methods failed
        state["errors"].append("All CAD generation engines failed")
        state["trace_log"].extend(result.trace_log)
        return state

    def _node_render(self, state: PipelineState) -> PipelineState:
        """Phase 5: Headless render for visual inspection."""
        self._emit_phase(state, Phase.RENDER)
        self._emit_trace(state, "Rendering design views")

        if not state.get("stl_path"):
            self._emit_trace(state, "No STL available for render")
            return state

        result = self.agents["cad_render"].run({
            "mesh_path": state["stl_path"],
            "design_id": state["design_id"],
            "run_id": state["run_id"],
            "patient_id": state["patient_id"],
        })

        if result.success:
            state["render_images"] = result.output_files
            self._emit_trace(state, f"✓ Rendered {len(result.output_files)} views")
        else:
            self._emit_trace(state, "Render failed — continuing without visual critique")

        state["trace_log"].extend(result.trace_log)
        return state

    def _node_vlm_critique(self, state: PipelineState) -> PipelineState:
        """Phase 6: VLM render-critique loop."""
        self._emit_phase(state, Phase.VLM_CRITIQUE)
        self._emit_trace(state, "Running VLM design critique")

        if not state.get("stl_path"):
            return state

        result = self.agents["vlm_critique"].run({
            "mesh_path": state["stl_path"],
            "design_id": state["design_id"],
            "constraints": state.get("constraints", {}),
            "run_id": state["run_id"],
            "patient_id": state["patient_id"],
        })

        if result.success:
            state["vlm_critique"] = result.output_data.get("critique", {})
            score = state["vlm_critique"].get("score", 0)
            self._emit_trace(state, f"✓ VLM critique score: {score}/10")
        else:
            state["vlm_critique"] = {"score": 0, "issues": ["VLM critique unavailable"]}
            state["warnings"].append("VLM critique could not be performed")

        state["trace_log"].extend(result.trace_log)
        return state

    def _node_fea(self, state: PipelineState) -> PipelineState:
        """Phase 7: FEA stress analysis (simplified)."""
        self._emit_phase(state, Phase.FEA)
        self._emit_trace(state, "Running FEA stress analysis")

        constraints = state.get("constraints", {})
        weight_kg = state["patient"].get("weight_kg", 20)
        dynamic_load = weight_kg * 9.81 * 1.5

        # Simplified FEA (in production: full FEA via CalculiX or similar)
        from config import FEA_DEFAULTS, MATERIALS
        material_key = constraints.get("material_recommendation", "petg")
        material = MATERIALS.get(material_key)

        thickness = constraints.get("wall_thickness_mm", 3.0)
        # Rough bending stress estimate
        wall_height = 180
        moment = dynamic_load * wall_height * 0.3
        section_mod = thickness * thickness * 30 / 6
        max_stress = moment / section_mod if section_mod > 0 else 999

        yield_strength = material.tensile_strength_mpa if material else 50
        von_mises_pct = (max_stress / yield_strength) * 100
        safety_factor = yield_strength / max_stress if max_stress > 0 else 0

        fea_result = {
            "passed": (safety_factor >= FEA_DEFAULTS.safety_factor and
                       von_mises_pct <= FEA_DEFAULTS.max_von_mises_pct),
            "max_von_mises_mpa": round(max_stress, 1),
            "von_mises_pct_yield": round(von_mises_pct, 1),
            "safety_factor": round(safety_factor, 2),
            "required_safety_factor": FEA_DEFAULTS.safety_factor,
            "dynamic_load_n": round(dynamic_load, 1),
            "material": material_key,
            "method": "simplified_beam_analysis",
            "note": "Full FEA (CalculiX mesh) recommended before manufacturing",
        }

        state["fea_result"] = fea_result
        status = "PASSED" if fea_result["passed"] else "FAILED"
        self._emit_trace(state, f"FEA {status}: SF={safety_factor:.2f}, σ_max={max_stress:.1f}MPa")

        if not fea_result["passed"]:
            state["warnings"].append(
                f"FEA safety factor {safety_factor:.2f} below minimum {FEA_DEFAULTS.safety_factor}. "
                f"Consider increasing wall thickness or adding lattice reinforcement."
            )

        self.db.add_audit(
            state["patient_id"], state["design_id"],
            "fea_analysis", "system",
            f"FEA {status}: SF={safety_factor:.2f}",
        )
        return state

    def _node_lattice(self, state: PipelineState) -> PipelineState:
        """Phase 8: Titanium lattice reinforcement evaluation."""
        self._emit_phase(state, Phase.LATTICE)
        self._emit_trace(state, "Evaluating lattice reinforcement requirements")

        constraints = state.get("constraints", {})
        result = self.agents["agentic_alloy"].run({
            "dynamic_load_n": constraints.get("dynamic_load_n", 300),
            "severity": state.get("severity", "moderate"),
            "material": constraints.get("material_recommendation", "petg"),
            "wall_thickness_mm": constraints.get("wall_thickness_mm", 3.0),
            "run_id": state["run_id"],
            "patient_id": state["patient_id"],
        })

        evaluation = result.output_data.get("lattice_evaluation", {})
        state["lattice_evaluation"] = evaluation

        if evaluation.get("needs_reinforcement"):
            self._emit_trace(state, "⚠ Ti lattice reinforcement RECOMMENDED")
            state["warnings"].append("Titanium lattice reinforcement recommended for structural adequacy")
        else:
            self._emit_trace(state, "✓ Polymer-only construction sufficient")

        state["trace_log"].extend(result.trace_log)
        return state

    def _node_human_review(self, state: PipelineState) -> PipelineState:
        """Phase 9: MANDATORY human review gate."""
        self._emit_phase(state, Phase.HUMAN_REVIEW)
        self._emit_trace(state, "⏸ HUMAN REVIEW REQUIRED — Pipeline paused")

        if not HUMAN_REVIEW_REQUIRED:
            # This should NEVER happen in production
            logger.critical("HUMAN_REVIEW_REQUIRED is False — this is a compliance violation!")
            state["errors"].append("CRITICAL: Human review gate bypassed — compliance violation")
            return state

        # Emit callback to GUI for human review dialog
        if self._on_human_review_needed:
            self._on_human_review_needed(state)

        # The human_approved flag will be set by the GUI callback
        # Pipeline execution pauses here until human approves
        self.db.add_audit(
            state["patient_id"], state["design_id"],
            "review_requested", "system",
            "Human review gate reached — awaiting clinician approval",
        )
        return state

    def approve_design(self, state: PipelineState, reviewer: str,
                       notes: str = "") -> PipelineState:
        """Called by GUI when human approves the design."""
        state["human_approved"] = True
        state["human_reviewer"] = reviewer
        state["review_notes"] = notes

        self.db.add_audit(
            state["patient_id"], state["design_id"],
            "approve", f"human:{reviewer}",
            f"Design approved by {reviewer}. Notes: {notes}",
            file_path=state.get("stl_path"),
        )
        self.db.update_design(state["design_id"], {
            "human_approved": 1,
            "human_reviewer": reviewer,
            "review_timestamp": datetime.now(timezone.utc).isoformat(),
        })

        self._emit_trace(state, f"✓ Design APPROVED by {reviewer}")
        return state

    def reject_design(self, state: PipelineState, reviewer: str,
                      reason: str) -> PipelineState:
        """Called by GUI when human rejects the design."""
        state["human_approved"] = False
        state["human_reviewer"] = reviewer
        state["review_notes"] = reason

        self.db.add_audit(
            state["patient_id"], state["design_id"],
            "reject", f"human:{reviewer}",
            f"Design REJECTED by {reviewer}. Reason: {reason}",
        )
        self._emit_trace(state, f"✗ Design REJECTED by {reviewer}: {reason}")
        return state

    def _node_export(self, state: PipelineState) -> PipelineState:
        """Phase 10: Export STL/STEP + generate audit PDF."""
        self._emit_phase(state, Phase.EXPORT)
        self._emit_trace(state, "Exporting design files and audit report")

        export_paths = []
        if state.get("stl_path"):
            export_paths.append(state["stl_path"])
        if state.get("step_path"):
            export_paths.append(state["step_path"])

        state["export_paths"] = export_paths

        # Generate audit PDF
        try:
            from export import AuditPDFGenerator
            pdf_gen = AuditPDFGenerator(self.db)
            pdf_path = pdf_gen.generate(
                patient_id=state["patient_id"],
                design_id=state["design_id"],
                state=state,
            )
            state["audit_pdf_path"] = pdf_path
            export_paths.append(pdf_path)
            self._emit_trace(state, f"✓ Audit PDF generated: {pdf_path}")
        except (ImportError, OSError, ValueError) as e:
            self._emit_trace(state, f"Audit PDF generation failed: {e}")
            state["warnings"].append(f"Audit PDF generation failed: {e}")

        self.db.add_audit(
            state["patient_id"], state["design_id"],
            "export", "system",
            f"Exported {len(export_paths)} files",
            file_path=state.get("stl_path"),
        )
        return state

    def _node_print(self, state: PipelineState) -> PipelineState:
        """Phase 11: Queue to printer via MCP broker."""
        self._emit_phase(state, Phase.PRINT)
        self._emit_trace(state, "Queuing to print via MCP broker")

        # Check printer status
        status_result = self.agents["octo_mcp"].run({
            "action": "status",
            "run_id": state["run_id"],
            "patient_id": state["patient_id"],
        })
        state["printer_status"] = status_result.output_data.get("printer_status", {})

        printer_state = state["printer_status"].get("state", "offline")
        if printer_state == "offline":
            self._emit_trace(state, "Printer is offline — print not queued")
            state["print_queued"] = False
            return state

        # Upload and start print
        stl_path = state.get("stl_path", "")
        upload_result = self.agents["octo_mcp"].run({
            "action": "upload",
            "gcode_path": stl_path,  # In production: slice STL → G-code first
            "run_id": state["run_id"],
            "patient_id": state["patient_id"],
        })

        if upload_result.output_data.get("uploaded"):
            state["print_queued"] = True
            self._emit_trace(state, "✓ Print job queued")
            self.db.add_audit(
                state["patient_id"], state["design_id"],
                "print", "system", "Print job queued to local printer",
            )
        else:
            state["print_queued"] = False
            self._emit_trace(state, "Print upload failed")

        state["trace_log"].extend(status_result.trace_log)
        return state

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------
    def _record_design(self, state: PipelineState):
        """Save design record to database."""
        record = DesignRecord(
            design_id=state["design_id"],
            patient_id=state["patient_id"],
            preset_key=state["preset_key"],
            parameters_json=json.dumps(state.get("constraints", {})),
            cad_engine_used=state["cad_engine"],
            stl_path=state.get("stl_path"),
            step_path=state.get("step_path"),
            iteration_count=state.get("iteration_count", 0),
        )
        self.db.create_design(record)
