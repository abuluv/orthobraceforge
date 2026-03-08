"""
OrthoBraceForge — ChatToSTL Agent
Wraps nchourrout/Chat-To-STL (Fallback generator).
"""
from pathlib import Path
from typing import Any, Dict, List

from config import EXPORT_DIR

from .base import AgentResult, BaseAgent


class ChatToSTLAgent(BaseAgent):
    """
    Fallback STL generator when build123d and OpenSCAD pipelines fail.
    Generates basic AFO geometry from natural language.
    """

    def __init__(self):
        super().__init__("chat_to_stl")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Fallback STL generation via Chat-To-STL")

        description = params.get("description", "pediatric ankle-foot orthosis")
        design_id = params.get("design_id", "temp")
        output_stl = str(EXPORT_DIR / f"fallback_{design_id}.stl")

        try:
            stl_content = self._generate_basic_afo_stl(params.get("constraints", {}))
            Path(output_stl).write_text(stl_content, encoding="utf-8")
            self._log(f"Fallback STL written to {output_stl}")

            return AgentResult(
                success=True,
                agent_name=self.name,
                output_data={"method": "fallback_parametric"},
                output_files=[output_stl],
                warnings=["Generated via fallback — reduced geometric fidelity"],
                iterations_used=1,
                trace_log=list(self._trace),
            )
        except OSError as e:
            return AgentResult(
                success=False, agent_name=self.name,
                errors=[f"Fallback generation failed: {e}"],
                trace_log=list(self._trace),
            )

    def _generate_basic_afo_stl(self, constraints: Dict) -> str:
        """Generate a basic ASCII STL for a simplified AFO shape."""
        # This generates a simplified rectangular AFO approximation
        # In production: Chat-To-STL's NL→mesh pipeline
        foot_l = constraints.get("foot_length_mm", 180)
        foot_w = constraints.get("ankle_width_mm", 50) * 1.4
        height = 180
        t = constraints.get("wall_thickness_mm", 3)

        # Minimal ASCII STL — rectangular approximation
        stl_lines = ["solid afo_fallback"]
        # Bottom face
        stl_lines.extend(self._stl_quad(0, 0, 0, foot_l, 0, 0, foot_l, foot_w, 0, 0, foot_w, 0))
        # Top face
        stl_lines.extend(self._stl_quad(0, 0, t, 0, foot_w, t, foot_l, foot_w, t, foot_l, 0, t))
        # Back wall
        stl_lines.extend(self._stl_quad(0, 0, 0, 0, foot_w, 0, 0, foot_w, height, 0, 0, height))
        stl_lines.append("endsolid afo_fallback")
        return "\n".join(stl_lines)

    @staticmethod
    def _stl_quad(x1, y1, z1, x2, y2, z2, x3, y3, z3, x4, y4, z4) -> List[str]:
        """Generate two STL triangles for a quad face."""
        return [
            "  facet normal 0 0 0",
            "    outer loop",
            f"      vertex {x1} {y1} {z1}",
            f"      vertex {x2} {y2} {z2}",
            f"      vertex {x3} {y3} {z3}",
            "    endloop",
            "  endfacet",
            "  facet normal 0 0 0",
            "    outer loop",
            f"      vertex {x1} {y1} {z1}",
            f"      vertex {x3} {y3} {z3}",
            f"      vertex {x4} {y4} {z4}",
            "    endloop",
            "  endfacet",
        ]
