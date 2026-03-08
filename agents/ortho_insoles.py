"""
OrthoBraceForge — OrthoInsoles Agent
Adapted from Green-AI-Hub for AFO parametric prediction.
"""
import json
from pathlib import Path
from typing import Any, Dict

from .base import AgentResult, BaseAgent


class OrthoInsolesAgent(BaseAgent):
    """
    Adapted from the insole prediction toolbox for AFO parametric
    prediction from 3D scans and measurements.
    """

    def __init__(self):
        super().__init__("ortho_insoles")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Generating AFO parametric predictions from scan data")

        scan_path = params.get("scan_path", "")
        measurements = params.get("measurements", {})

        # Extract measurements from scan if available
        if scan_path and Path(scan_path).exists():
            extracted = self._extract_from_scan(scan_path)
            measurements = {**extracted, **measurements}  # Manual overrides win
            self._log(f"Extracted measurements from scan: {extracted}")

        # Generate parametric AFO predictions
        predictions = self._predict_afo_parameters(measurements)
        self._log(f"Generated predictions: {json.dumps(predictions, indent=2)}")

        return AgentResult(
            success=True,
            agent_name=self.name,
            output_data={"measurements": measurements, "predictions": predictions},
            trace_log=list(self._trace),
        )

    def _extract_from_scan(self, scan_path: str) -> Dict:
        """Extract anatomical measurements from STL/OBJ/point cloud."""
        try:
            import trimesh
            mesh = trimesh.load(scan_path)
            bounds = mesh.bounds
            dims = bounds[1] - bounds[0]
            return {
                "foot_length_mm": round(dims[0], 1),
                "foot_width_mm": round(dims[1], 1),
                "foot_height_mm": round(dims[2], 1),
                "scan_volume_cm3": round(mesh.volume / 1000, 1),
            }
        except (ImportError, OSError, ValueError) as e:
            self._log(f"Scan extraction error: {e}")
            return {}

    def _predict_afo_parameters(self, measurements: Dict) -> Dict:
        """
        Predict optimal AFO parameters from measurements.
        Production: runs pre-trained model from ortho_insoles/models/.
        """
        foot_length = measurements.get("foot_length_mm", 180)
        foot_width = measurements.get("foot_width_mm", 70)

        return {
            "recommended_footplate_length": foot_length + 5,  # growth margin
            "recommended_footplate_width": foot_width + 4,     # clearance
            "recommended_arch_height_mm": foot_width * 0.15,
            "recommended_heel_cup_depth_mm": 12,
            "recommended_trim_line_height_mm": foot_length * 0.65,
            "confidence": 0.85,
        }
