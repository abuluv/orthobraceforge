"""
OrthoBraceForge — AgenticAlloy Agent
Wraps BaratiLab (Titanium lattice evaluation).
"""
import json
from typing import Any, Dict

from config import FEA_DEFAULTS, MATERIALS

from .base import AgentResult, BaseAgent


class AgenticAlloyAgent(BaseAgent):
    """
    Evaluates titanium lattice reinforcement designs for severe equinus AFOs.
    Determines if polymer-only construction is sufficient or if Ti inserts needed.
    """

    def __init__(self):
        super().__init__("agentic_alloy")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Evaluating lattice reinforcement requirements")

        load_n = params.get("dynamic_load_n", 300)
        severity = params.get("severity", "moderate")
        material = params.get("material", "petg")
        thickness = params.get("wall_thickness_mm", 3.0)

        evaluation = self._evaluate_reinforcement(load_n, severity, material, thickness)
        self._log(f"Evaluation result: {json.dumps(evaluation, indent=2)}")

        return AgentResult(
            success=True,
            agent_name=self.name,
            output_data={"lattice_evaluation": evaluation},
            trace_log=list(self._trace),
        )

    def _evaluate_reinforcement(self, load_n: float, severity: str,
                                  material: str, thickness: float) -> Dict:
        """Determine if titanium lattice reinforcement is needed."""
        mat = MATERIALS.get(material)
        if not mat:
            return {"needs_reinforcement": False, "reason": "Unknown material"}

        # Simplified stress check
        # Approximate bending stress in posterior wall
        wall_height = 180  # mm typical
        moment = load_n * wall_height * 0.3  # rough bending moment
        section_modulus = thickness * thickness * 30 / 6  # rough section modulus
        stress_mpa = moment / section_modulus if section_modulus > 0 else 999

        safety_factor = mat.tensile_strength_mpa / stress_mpa if stress_mpa > 0 else 0
        needs_reinforcement = safety_factor < FEA_DEFAULTS.safety_factor

        lattice_spec = None
        if needs_reinforcement:
            lattice_spec = {
                "type": "BCC",
                "relative_density": 0.6,
                "strut_diameter_mm": 0.5,
                "cell_size_mm": 3.0,
                "material": "Ti-6Al-4V",
                "location": "posterior_wall_reinforcement_rib",
                "dimensions_mm": [thickness, 15, wall_height * 0.5],
            }

        return {
            "needs_reinforcement": needs_reinforcement,
            "estimated_stress_mpa": round(stress_mpa, 1),
            "material_yield_mpa": mat.tensile_strength_mpa,
            "safety_factor_without_lattice": round(safety_factor, 2),
            "required_safety_factor": FEA_DEFAULTS.safety_factor,
            "lattice_specification": lattice_spec,
            "severity_input": severity,
        }
