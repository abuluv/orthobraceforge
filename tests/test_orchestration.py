"""
Integration tests for OrthoBraceForge orchestration pipeline.
Tests the full pipeline flow, phase transitions, compliance blocking,
CAD fallback chains, human review gate, and error recovery.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from agents import AgentResult
from database import Database
from orchestration import OrchoBraceOrchestrator, Phase, PipelineState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SAMPLE_PATIENT = {
    "first_name": "Test",
    "last_name": "Patient",
    "dob": "2020-01-01",
    "age": 6,
    "weight_kg": 22,
    "height_cm": 115,
    "laterality": "bilateral",
    "severity": "moderate",
    "notes": "Test",
}


def _success_result(agent_name, output_data=None, output_files=None, iterations=1):
    """Build a successful AgentResult with sensible defaults."""
    return AgentResult(
        success=True,
        agent_name=agent_name,
        output_data=output_data or {},
        output_files=output_files or [],
        errors=[],
        warnings=[],
        iterations_used=iterations,
        trace_log=[f"{agent_name} executed"],
    )


def _failure_result(agent_name, errors=None):
    """Build a failed AgentResult."""
    return AgentResult(
        success=False,
        agent_name=agent_name,
        output_data={},
        output_files=[],
        errors=errors or [f"{agent_name} failed"],
        warnings=[],
        iterations_used=0,
        trace_log=[f"{agent_name} failed"],
    )


@pytest.fixture
def db(tmp_path):
    """Create a fresh SQLite database in a temp directory."""
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture
def orchestrator(db):
    """Create an orchestrator with all agents mocked to succeed by default."""
    orch = OrchoBraceOrchestrator.__new__(OrchoBraceOrchestrator)
    orch.db = db
    orch.rag = MagicMock()
    orch._on_phase_change = None
    orch._on_trace_update = None
    orch._on_human_review_needed = None
    orch._on_error = None

    # Default compliance RAG returns passing result
    orch.rag.check_design_compliance.return_value = {
        "passed": True,
        "flags": ["HUMAN_REVIEW_MANDATORY"],
        "blocking_issues": [],
        "warnings": [],
        "recommendations": [],
    }
    orch.rag.get_design_constraints.return_value = {
        "preset": "Mild Bilateral Idiopathic Toe Walking",
        "afo_type": "posterior_leaf_spring",
        "ankle_target_deg": 5.0,
        "plantar_stop_deg": 0.0,
        "wall_thickness_mm": 3.0,
        "trim_line": "medial_trim",
        "flex_zone": True,
        "foot_length_range_mm": (165, 200),
        "ankle_width_range_mm": (46, 55),
        "dynamic_load_n": 323.7,
        "safety_factor": 3.0,
        "max_von_mises_pct": 60.0,
        "fatigue_cycles": 1_000_000,
        "material_recommendation": "petg",
        "growth_accommodation_mm": 5.0,
        "replacement_interval_months": 6,
        "regulatory_classification": "INVESTIGATIONAL USE ONLY",
    }

    # Build mock agents
    stl_path = "/tmp/test_design.stl"
    step_path = "/tmp/test_design.step"

    orch.agents = {
        "forma_ai": MagicMock(),
        "agentic3d": MagicMock(),
        "talkcad": MagicMock(),
        "cad_render": MagicMock(),
        "vlm_critique": MagicMock(),
        "llm_3d_print": MagicMock(),
        "ortho_insoles": MagicMock(),
        "octo_mcp": MagicMock(),
        "agentic_alloy": MagicMock(),
        "chat_to_stl": MagicMock(),
    }

    # Default execute returns for every agent
    orch.agents["ortho_insoles"].run.return_value = _success_result(
        "ortho_insoles",
        output_data={
            "predictions": {
                "recommended_footplate_length": 180,
                "recommended_footplate_width": 70,
            },
            "measurements": {"foot_length": 180, "ankle_width": 50},
        },
    )
    orch.agents["forma_ai"].run.return_value = _success_result(
        "forma_ai",
        output_data={"build123d_code": "# mock code"},
        output_files=[stl_path, step_path],
        iterations=3,
    )
    orch.agents["agentic3d"].run.return_value = _success_result(
        "agentic3d",
        output_files=[stl_path],
        iterations=2,
    )
    orch.agents["chat_to_stl"].run.return_value = _success_result(
        "chat_to_stl",
        output_files=[stl_path],
        iterations=1,
    )
    orch.agents["cad_render"].run.return_value = _success_result(
        "cad_render",
        output_files=["/tmp/render_front.png", "/tmp/render_side.png"],
    )
    orch.agents["vlm_critique"].run.return_value = _success_result(
        "vlm_critique",
        output_data={"critique": {"score": 8, "issues": []}},
    )
    orch.agents["agentic_alloy"].run.return_value = _success_result(
        "agentic_alloy",
        output_data={"lattice_evaluation": {"needs_reinforcement": False}},
    )
    orch.agents["octo_mcp"].run.return_value = _success_result(
        "octo_mcp",
        output_data={"printer_status": {"state": "operational"}},
    )

    return orch


# ---------------------------------------------------------------------------
# 1. End-to-end pipeline reaches HUMAN_REVIEW
# ---------------------------------------------------------------------------
class TestEndToEndPipeline:
    def test_pipeline_reaches_human_review(self, orchestrator):
        """Full pipeline with all agents succeeding should pause at HUMAN_REVIEW."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["phase"] == Phase.HUMAN_REVIEW.value
        assert state["human_approved"] is False
        assert state.get("stl_path") is not None
        assert state.get("fea_result") is not None
        assert state.get("vlm_critique") is not None
        assert len(state["errors"]) == 0

    def test_pipeline_has_valid_ids(self, orchestrator):
        """Pipeline should assign run_id, patient_id, and design_id."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state.get("run_id") is not None
        assert state.get("patient_id") is not None
        assert state.get("design_id") is not None
        assert len(state["run_id"]) == 36  # UUID format


# ---------------------------------------------------------------------------
# 2. Phase transitions
# ---------------------------------------------------------------------------
class TestPhaseTransitions:
    def test_phase_order_through_pipeline(self, orchestrator):
        """Verify that phases are visited in the correct order."""
        visited_phases = []

        def track_phase(phase_value, state):
            visited_phases.append(phase_value)

        orchestrator.set_callbacks(on_phase_change=track_phase)

        orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        expected_phases = [
            Phase.INTAKE.value,
            Phase.COMPLIANCE.value,
            Phase.PARAMETRIC.value,
            Phase.CAD_GEN.value,
            Phase.RENDER.value,
            Phase.VLM_CRITIQUE.value,
            Phase.FEA.value,
            Phase.LATTICE.value,
            Phase.HUMAN_REVIEW.value,
        ]
        assert visited_phases == expected_phases

    def test_state_phase_updates_at_each_node(self, orchestrator):
        """Each node should update state['phase'] to its phase value."""
        phases_seen = []
        original_emit = orchestrator._emit_phase

        def intercept_emit(state, phase):
            phases_seen.append(phase.value)
            original_emit(state, phase)

        orchestrator._emit_phase = intercept_emit

        orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        # All expected phases should be visited
        assert Phase.INTAKE.value in phases_seen
        assert Phase.COMPLIANCE.value in phases_seen
        assert Phase.HUMAN_REVIEW.value in phases_seen


# ---------------------------------------------------------------------------
# 3 & 4. Compliance blocking
# ---------------------------------------------------------------------------
class TestComplianceBlocking:
    def test_invalid_preset_blocks_pipeline(self, orchestrator):
        """An unknown preset_key should cause the pipeline to enter ERROR state."""
        # Override the RAG mock: _node_compliance checks TOE_WALKING_PRESETS first
        # before calling the RAG, so we need to use a real compliance node behavior.
        # The preset lookup happens before the RAG call, and with an invalid key
        # it sets compliance_result with passed=False and blocking_issues.
        # We need to let _node_compliance actually run its preset check logic.
        # Re-attach the real rag but mock it to avoid side effects.
        orchestrator.rag.check_design_compliance.return_value = {
            "passed": False,
            "flags": [],
            "blocking_issues": ["Unknown preset: nonexistent_preset"],
            "warnings": [],
            "recommendations": [],
        }

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="nonexistent_preset",
        )

        assert state["phase"] == Phase.ERROR.value
        assert any("Unknown preset" in e for e in state["errors"])

    def test_underage_patient_blocks_pipeline(self, orchestrator):
        """A patient under age 2 should be blocked by compliance."""
        orchestrator.rag.check_design_compliance.return_value = {
            "passed": False,
            "flags": ["AGE_CONTRAINDICATED"],
            "blocking_issues": [
                "Patient age <2 years. AFO intervention for toe walking is "
                "not indicated before age 2."
            ],
            "warnings": [],
            "recommendations": [],
        }

        young_patient = SAMPLE_PATIENT.copy()
        young_patient["age"] = 1

        state = orchestrator.run_pipeline(
            patient_data=young_patient,
            preset_key="mild_bilateral",
        )

        assert state["phase"] == Phase.ERROR.value
        assert len(state["errors"]) > 0
        assert any("age" in e.lower() for e in state["errors"])


# ---------------------------------------------------------------------------
# 5. CAD generation fallback chain
# ---------------------------------------------------------------------------
class TestCADFallbackChain:
    def test_fallback_to_openscad_when_forma_fails(self, orchestrator):
        """When FormaAI (build123d) fails, should fall back to OpenSCAD (agentic3d)."""
        orchestrator.agents["forma_ai"].run.return_value = _failure_result("forma_ai")

        stl_path = "/tmp/openscad_output.stl"
        orchestrator.agents["agentic3d"].run.return_value = _success_result(
            "agentic3d",
            output_files=[stl_path],
            iterations=2,
        )

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["cad_engine"] == "openscad"
        assert state["stl_path"] == stl_path
        assert state["phase"] == Phase.HUMAN_REVIEW.value

    def test_fallback_to_chat_to_stl(self, orchestrator):
        """When both FormaAI and Agentic3D fail, should fall back to Chat-To-STL."""
        orchestrator.agents["forma_ai"].run.return_value = _failure_result("forma_ai")
        orchestrator.agents["agentic3d"].run.return_value = _failure_result("agentic3d")

        stl_path = "/tmp/chat_to_stl_output.stl"
        orchestrator.agents["chat_to_stl"].run.return_value = _success_result(
            "chat_to_stl",
            output_files=[stl_path],
            iterations=1,
        )

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["cad_engine"] == "chat_to_stl"
        assert state["stl_path"] == stl_path


# ---------------------------------------------------------------------------
# 6. All CAD engines fail
# ---------------------------------------------------------------------------
class TestAllCADEnginesFail:
    def test_error_state_when_all_cad_engines_fail(self, orchestrator):
        """When all three CAD engines fail, pipeline should enter ERROR state."""
        orchestrator.agents["forma_ai"].run.return_value = _failure_result("forma_ai")
        orchestrator.agents["agentic3d"].run.return_value = _failure_result("agentic3d")
        orchestrator.agents["chat_to_stl"].run.return_value = _failure_result("chat_to_stl")

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["phase"] == Phase.ERROR.value
        assert any("CAD generation" in e or "CAD" in e for e in state["errors"])
        assert state.get("stl_path") is None


# ---------------------------------------------------------------------------
# 7. approve_design
# ---------------------------------------------------------------------------
class TestApproveDesign:
    def test_approve_design_updates_state(self, orchestrator):
        """approve_design should set human_approved=True and record reviewer info."""
        # Run pipeline to get a state at HUMAN_REVIEW
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )
        assert state["phase"] == Phase.HUMAN_REVIEW.value

        state = orchestrator.approve_design(state, reviewer="Dr. Smith", notes="Looks good")

        assert state["human_approved"] is True
        assert state["human_reviewer"] == "Dr. Smith"
        assert state["review_notes"] == "Looks good"

    def test_approve_design_creates_audit_entry(self, orchestrator, db):
        """approve_design should create an audit trail entry."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        orchestrator.approve_design(state, reviewer="Dr. Smith", notes="Approved")

        audit_trail = db.get_audit_trail(state["patient_id"])
        approve_entries = [e for e in audit_trail if e.action == "approve"]
        assert len(approve_entries) == 1
        assert "Dr. Smith" in approve_entries[0].details

    def test_approve_design_updates_database(self, orchestrator, db):
        """approve_design should update the design record in the database."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        orchestrator.approve_design(state, reviewer="Dr. Smith", notes="OK")

        design = db.get_design(state["design_id"])
        assert design is not None
        assert design.human_approved is True
        assert design.human_reviewer == "Dr. Smith"


# ---------------------------------------------------------------------------
# 8. reject_design
# ---------------------------------------------------------------------------
class TestRejectDesign:
    def test_reject_design_updates_state(self, orchestrator):
        """reject_design should keep human_approved=False and record reason."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        state = orchestrator.reject_design(
            state, reviewer="Dr. Jones", reason="Wall too thin"
        )

        assert state["human_approved"] is False
        assert state["human_reviewer"] == "Dr. Jones"
        assert state["review_notes"] == "Wall too thin"

    def test_reject_design_creates_audit_entry(self, orchestrator, db):
        """reject_design should create a reject audit trail entry."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        orchestrator.reject_design(state, reviewer="Dr. Jones", reason="Needs revision")

        audit_trail = db.get_audit_trail(state["patient_id"])
        reject_entries = [e for e in audit_trail if e.action == "reject"]
        assert len(reject_entries) == 1
        assert "REJECTED" in reject_entries[0].details


# ---------------------------------------------------------------------------
# 9. FEA computation
# ---------------------------------------------------------------------------
class TestFEAComputation:
    def test_fea_result_structure(self, orchestrator):
        """FEA result should contain all required fields."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        fea = state.get("fea_result")
        assert fea is not None
        assert "passed" in fea
        assert "max_von_mises_mpa" in fea
        assert "von_mises_pct_yield" in fea
        assert "safety_factor" in fea
        assert "required_safety_factor" in fea
        assert "dynamic_load_n" in fea
        assert "material" in fea
        assert "method" in fea
        assert isinstance(fea["passed"], bool)
        assert isinstance(fea["safety_factor"], float)

    def test_fea_dynamic_load_matches_patient_weight(self, orchestrator):
        """Dynamic load should be calculated from patient weight (weight * 9.81 * 1.5)."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        fea = state["fea_result"]
        expected_load = 22 * 9.81 * 1.5
        assert abs(fea["dynamic_load_n"] - round(expected_load, 1)) < 0.2

    def test_fea_uses_material_from_constraints(self, orchestrator):
        """FEA should use the material recommended by constraints."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        fea = state["fea_result"]
        assert fea["material"] in ("petg", "nylon_pa12", "tpu_95a", "ti6al4v_lattice")


# ---------------------------------------------------------------------------
# 10. HUMAN_REVIEW_REQUIRED gate
# ---------------------------------------------------------------------------
class TestHumanReviewGate:
    def test_pipeline_pauses_at_human_review(self, orchestrator):
        """Pipeline must pause at HUMAN_REVIEW when human_approved=False."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["phase"] == Phase.HUMAN_REVIEW.value
        assert state["human_approved"] is False
        # Export phase should NOT have been reached
        assert len(state.get("export_paths", [])) == 0

    def test_human_review_callback_invoked(self, orchestrator):
        """The on_human_review_needed callback should be called."""
        callback = MagicMock()
        orchestrator.set_callbacks(on_human_review_needed=callback)

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0]["phase"] == Phase.HUMAN_REVIEW.value

    def test_pipeline_does_not_export_without_approval(self, orchestrator):
        """Without human approval, the pipeline should not reach EXPORT or COMPLETE."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["phase"] != Phase.EXPORT.value
        assert state["phase"] != Phase.COMPLETE.value

    @patch("orchestration.HUMAN_REVIEW_REQUIRED", True)
    def test_trace_log_contains_human_review_pause(self, orchestrator):
        """Trace log should indicate pipeline paused for human review."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert any("human review" in t.lower() or "awaiting" in t.lower()
                    for t in state["trace_log"])


# ---------------------------------------------------------------------------
# 11. Error recovery
# ---------------------------------------------------------------------------
class TestErrorRecovery:
    def test_exception_in_node_enters_error_phase(self, orchestrator):
        """An exception raised in a pipeline node should result in ERROR phase."""
        orchestrator.agents["ortho_insoles"].run.side_effect = RuntimeError(
            "Simulated agent crash"
        )

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["phase"] == Phase.ERROR.value
        assert any("Simulated agent crash" in e for e in state["errors"])

    def test_exception_in_render_enters_error_phase(self, orchestrator):
        """An exception in the render node should result in ERROR phase."""
        orchestrator.agents["cad_render"].run.side_effect = ValueError(
            "Render engine exploded"
        )

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["phase"] == Phase.ERROR.value
        assert any("Render engine exploded" in e for e in state["errors"])

    def test_exception_preserves_partial_state(self, orchestrator):
        """Even after an exception, state should contain data from completed phases."""
        # Let parametric fail, so intake and compliance succeed first
        orchestrator.agents["ortho_insoles"].run.side_effect = RuntimeError("boom")

        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert state["phase"] == Phase.ERROR.value
        # Intake and compliance should have completed
        assert state.get("patient_id") is not None
        assert state.get("compliance_result") is not None


# ---------------------------------------------------------------------------
# Additional integration tests
# ---------------------------------------------------------------------------
class TestCallbacks:
    def test_set_callbacks(self, orchestrator):
        """set_callbacks should register callback functions."""
        cb1 = MagicMock()
        cb2 = MagicMock()
        cb3 = MagicMock()

        orchestrator.set_callbacks(
            on_phase_change=cb1,
            on_trace_update=cb2,
            on_human_review_needed=cb3,
        )

        assert orchestrator._on_phase_change is cb1
        assert orchestrator._on_trace_update is cb2
        assert orchestrator._on_human_review_needed is cb3

    def test_phase_change_callback_called_for_each_phase(self, orchestrator):
        """on_phase_change should be called at each pipeline phase."""
        phase_callback = MagicMock()
        orchestrator.set_callbacks(on_phase_change=phase_callback)

        orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        # Should be called for every phase reached
        assert phase_callback.call_count >= 9  # INTAKE through HUMAN_REVIEW

    def test_trace_update_callback_called(self, orchestrator):
        """on_trace_update should be called with trace messages."""
        trace_callback = MagicMock()
        orchestrator.set_callbacks(on_trace_update=trace_callback)

        orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        assert trace_callback.call_count > 0


class TestDatabaseIntegration:
    def test_patient_record_created(self, orchestrator, db):
        """Pipeline should create a patient record in the database."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        patient = db.get_patient(state["patient_id"])
        assert patient is not None
        assert patient.first_name == "Test"
        assert patient.last_name == "Patient"
        assert patient.age_years == 6

    def test_design_record_created(self, orchestrator, db):
        """Pipeline should create a design record in the database."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        design = db.get_design(state["design_id"])
        assert design is not None
        assert design.preset_key == "mild_bilateral"

    def test_audit_trail_populated(self, orchestrator, db):
        """Pipeline should create audit trail entries."""
        state = orchestrator.run_pipeline(
            patient_data=SAMPLE_PATIENT.copy(),
            preset_key="mild_bilateral",
        )

        trail = db.get_audit_trail(state["patient_id"])
        assert len(trail) > 0
        actions = [e.action for e in trail]
        assert "create" in actions
        assert "compliance_check" in actions
