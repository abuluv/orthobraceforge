"""
OrthoBraceForge — Print Defect Agent
Wraps BaratiLab/LLM-3D-Print (Printer defect correction).
"""
from pathlib import Path
from typing import Any, Dict, List

from .base import AgentResult, BaseAgent


class PrintDefectAgent(BaseAgent):
    """
    Wraps the LLM-3D-Print defect monitoring and correction system.
    Analyzes print-in-progress images to detect and correct defects.
    """

    def __init__(self):
        super().__init__("llm_3d_print")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Analyzing print for defects")

        image_path = params.get("image_path", "")
        gcode_path = params.get("gcode_path", "")
        layer_number = params.get("layer_number", 0)

        if not Path(image_path).exists():
            return AgentResult(
                success=False, agent_name=self.name,
                errors=["Print image not found for analysis"],
                trace_log=list(self._trace),
            )

        # Analyze for common FDM defects
        defects = self._detect_defects(image_path)
        corrections = self._generate_corrections(defects, layer_number)

        self._log(f"Detected {len(defects)} defects, generated {len(corrections)} corrections")

        return AgentResult(
            success=True,
            agent_name=self.name,
            output_data={
                "defects": defects,
                "corrections": corrections,
                "layer_analyzed": layer_number,
                "action": "pause" if any(d["severity"] == "critical" for d in defects) else "continue",
            },
            trace_log=list(self._trace),
        )

    def _detect_defects(self, image_path: str) -> List[Dict]:
        """
        Detect print defects from image.
        Production: runs pre-trained CNN/VLM model.
        Stub: returns empty list (no defects detected).
        """
        self._log("Running defect detection model")
        # In production: load model from vendored/llm_3d_print/models/
        # and run inference on image
        return []

    def _generate_corrections(self, defects: List[Dict],
                               layer: int) -> List[Dict]:
        """Generate G-code corrections for detected defects."""
        corrections = []
        for defect in defects:
            if defect.get("type") == "under_extrusion":
                corrections.append({
                    "type": "adjust_flow_rate",
                    "value": 1.05,  # +5% flow
                    "layer": layer,
                })
            elif defect.get("type") == "warping":
                corrections.append({
                    "type": "adjust_bed_temp",
                    "value": 5,  # +5°C
                    "layer": layer,
                })
            elif defect.get("type") == "stringing":
                corrections.append({
                    "type": "adjust_retraction",
                    "value": 0.5,  # +0.5mm retraction
                    "layer": layer,
                })
        return corrections
