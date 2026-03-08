"""
Tests for the custom exception hierarchy and agent error translation.
"""
from unittest.mock import MagicMock, patch

import pytest

from agents import (
    Agentic3DAgent,
    AgentResult,
    BaseAgent,
    ChatToSTLAgent,
    FormaAIAgent,
    OctoMCPAgent,
)
from exceptions import (
    CADGenerationError,
    ComplianceError,
    MeasurementValidationError,
    OrthoError,
    PrinterConnectionError,
)


# ===========================================================================
# Exception hierarchy tests
# ===========================================================================
class TestExceptionHierarchy:
    def test_ortho_error_is_exception(self):
        assert issubclass(OrthoError, Exception)

    def test_compliance_error_inherits(self):
        assert issubclass(ComplianceError, OrthoError)

    def test_cad_generation_error_inherits(self):
        assert issubclass(CADGenerationError, OrthoError)

    def test_printer_connection_error_inherits(self):
        assert issubclass(PrinterConnectionError, OrthoError)

    def test_measurement_validation_error_inherits(self):
        assert issubclass(MeasurementValidationError, OrthoError)

    def test_can_catch_all_domain_errors(self):
        """except OrthoError should catch all domain exceptions."""
        for exc_cls in (ComplianceError, CADGenerationError,
                        PrinterConnectionError, MeasurementValidationError):
            with pytest.raises(OrthoError):
                raise exc_cls("test")


class TestExceptionStringRepresentation:
    def test_ortho_error_str_without_context(self):
        e = OrthoError("something failed")
        assert str(e) == "something failed"

    def test_ortho_error_str_with_context(self):
        e = OrthoError("fail", context={"run_id": "R1", "agent": "forma"})
        s = str(e)
        assert "fail" in s
        assert "run_id=R1" in s
        assert "agent=forma" in s

    def test_cad_generation_error_includes_engine(self):
        e = CADGenerationError("render failed", engine="openscad")
        assert "engine=openscad" in str(e)
        assert e.engine == "openscad"

    def test_measurement_validation_error_fields(self):
        e = MeasurementValidationError(
            "out of range", field="foot_length", value=300,
            valid_range=(100, 275),
        )
        assert e.field == "foot_length"
        assert e.value == 300
        assert e.valid_range == (100, 275)
        s = str(e)
        assert "foot_length" in s
        assert "300" in s

    def test_ortho_error_base_message(self):
        e = OrthoError("base msg", context={"key": "val"})
        assert e.base_message == "base msg"
        assert e.context == {"key": "val"}


# ===========================================================================
# BaseAgent.run() wrapper tests
# ===========================================================================
class TestBaseAgentRun:
    def _make_agent(self):
        """Create a concrete agent subclass for testing."""
        class DummyAgent(BaseAgent):
            def execute(self, params):
                return AgentResult(success=True, agent_name=self.name)
        return DummyAgent("test_agent")

    def test_run_logs_start_and_end(self):
        agent = self._make_agent()
        result = agent.run({"run_id": "R1", "patient_id": "P1"})
        assert result.success
        trace = agent._trace
        assert any("START execute" in t for t in trace)
        assert any("END execute" in t for t in trace)
        assert any("run_id=R1" in t for t in trace)
        assert any("patient_id=P1" in t for t in trace)

    def test_run_logs_elapsed_time(self):
        agent = self._make_agent()
        agent.run({})
        end_entry = [t for t in agent._trace if "END execute" in t][0]
        assert "elapsed=" in end_entry

    def test_run_logs_failed_on_exception(self):
        class FailAgent(BaseAgent):
            def execute(self, params):
                raise RuntimeError("boom")
        agent = FailAgent("fail_agent")
        with pytest.raises(RuntimeError, match="boom"):
            agent.run({})
        trace = agent._trace
        assert any("FAILED execute" in t for t in trace)
        assert any("boom" in t for t in trace)

    def test_run_delegates_to_execute(self):
        agent = self._make_agent()
        result = agent.run({"key": "val"})
        assert result.agent_name == "test_agent"
        assert result.success is True


# ===========================================================================
# Agent error translation tests
# ===========================================================================
class TestAgentErrorTranslation:
    @patch("agents.subprocess.run")
    def test_agentic3d_handles_oserror_in_render(self, mock_run):
        """OSError in render should not crash agent, returns failure result."""
        mock_run.side_effect = OSError("disk full")
        agent = Agentic3DAgent()
        result = agent.execute({
            "description": "test",
            "constraints": {},
            "max_iterations": 1,
        })
        # Agent catches the OSError in _render_stl and reports failure
        assert not result.success
        assert len(result.errors) > 0

    @patch("agents.subprocess.run")
    def test_forma_handles_subprocess_timeout(self, mock_run):
        """Timeout in build123d should return failure, not raise."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=180)
        agent = FormaAIAgent()
        result = agent.execute({
            "constraints": {},
            "max_iterations": 1,
        })
        assert not result.success

    def test_octo_mcp_handles_no_api_key(self):
        """OctoMCPAgent without API key returns unconfigured status."""
        with patch.dict("os.environ", {}, clear=True):
            agent = OctoMCPAgent()
            agent._api_key = ""
            status = agent._get_printer_status()
            assert status["state"] == "unconfigured"

    def test_chat_to_stl_handles_oserror(self):
        """OSError during file write returns failure result."""
        agent = ChatToSTLAgent()
        with patch("agents.Path.write_text", side_effect=OSError("disk full")):
            result = agent.execute({"constraints": {}})
        assert not result.success
        assert any("disk full" in e for e in result.errors)


# ===========================================================================
# Pipeline exception layering test
# ===========================================================================
class TestPipelineExceptionHandling:
    def test_ortho_error_in_pipeline_produces_typed_message(self):
        """OrthoError should produce a message with the exception type name."""
        from unittest.mock import MagicMock

        from orchestration import OrchoBraceOrchestrator

        orch = OrchoBraceOrchestrator.__new__(OrchoBraceOrchestrator)
        orch.db = MagicMock()
        orch.rag = MagicMock()
        orch._on_phase_change = None
        orch._on_trace_update = None
        orch._on_human_review_needed = None
        orch._on_error = None
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

        # Make the first agent raise a ComplianceError
        orch.rag.check_design_compliance.side_effect = ComplianceError("Bad preset")

        state = orch.run_pipeline(
            patient_data={"name": "Test", "age": 7, "weight_kg": 23},
            preset_key="mild_bilateral",
        )
        assert any("ComplianceError" in e for e in state["errors"])

    def test_generic_exception_in_pipeline_uses_unexpected_prefix(self):
        """Non-OrthoError should produce 'Unexpected' error message."""
        from orchestration import OrchoBraceOrchestrator

        orch = OrchoBraceOrchestrator.__new__(OrchoBraceOrchestrator)
        orch.db = MagicMock()
        orch.rag = MagicMock()
        orch._on_phase_change = None
        orch._on_trace_update = None
        orch._on_human_review_needed = None
        orch._on_error = None
        orch.agents = {}

        orch.rag.check_design_compliance.side_effect = RuntimeError("unexpected boom")

        state = orch.run_pipeline(
            patient_data={"name": "Test", "age": 7, "weight_kg": 23},
            preset_key="mild_bilateral",
        )
        assert any("Unexpected" in e for e in state["errors"])
