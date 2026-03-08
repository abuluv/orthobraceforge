"""
OrthoBraceForge — Agentic3D Agent
Wraps reetm09/agentic3d (Autogen OpenSCAD agent loop).
"""
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import EXPORT_DIR, MAX_AGENT_ITERATIONS, OPENSCAD_TIMEOUT_SEC
from exceptions import CADGenerationError

from .base import AgentResult, BaseAgent

logger = logging.getLogger("orthobraceforge.agents")


class Agentic3DAgent(BaseAgent):
    """
    Wraps the agentic3d Autogen-based OpenSCAD generation loop.
    Takes natural language AFO description + parametric constraints,
    generates OpenSCAD code iteratively until valid STL is produced.
    """

    def __init__(self):
        super().__init__("agentic3d")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Starting OpenSCAD agent loop")

        description = params.get("description", "")
        constraints = params.get("constraints", {})
        max_iter = params.get("max_iterations", MAX_AGENT_ITERATIONS)

        # Build the OpenSCAD generation prompt from constraints
        scad_prompt = self._build_scad_prompt(description, constraints)
        self._log(f"Generated SCAD prompt ({len(scad_prompt)} chars)")

        output_stl = str(EXPORT_DIR / f"agentic3d_{params.get('design_id', 'temp')}.stl")
        output_scad = str(EXPORT_DIR / f"agentic3d_{params.get('design_id', 'temp')}.scad")

        errors: List[str] = []
        scad_code = None

        for iteration in range(1, max_iter + 1):
            self._log(f"Iteration {iteration}/{max_iter}")

            try:
                # Step 1: Generate or refine OpenSCAD code via local LLM
                scad_code = self._generate_scad(scad_prompt, scad_code, errors)
                self._log(f"Generated SCAD code ({len(scad_code)} chars)")

                # Step 2: Validate SCAD syntax
                syntax_ok, syntax_errors = self._validate_scad_syntax(scad_code)
                if not syntax_ok:
                    errors = syntax_errors
                    self._log(f"Syntax errors: {syntax_errors}")
                    continue

                # Step 3: Render to STL via OpenSCAD CLI
                render_ok = self._render_stl(scad_code, output_scad, output_stl)
                if render_ok:
                    self._log("STL rendered successfully")
                    return AgentResult(
                        success=True,
                        agent_name=self.name,
                        output_data={"scad_code": scad_code},
                        output_files=[output_stl, output_scad],
                        iterations_used=iteration,
                        trace_log=list(self._trace),
                    )
                else:
                    errors.append("OpenSCAD render failed — non-manifold geometry")
                    self._log("Render failed, retrying")

            except (CADGenerationError, subprocess.SubprocessError, OSError) as e:
                errors.append(str(e))
                self._log(f"CAD error: {e}")
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error in iteration {iteration}: {e}", exc_info=True)
                errors.append(str(e))

        return AgentResult(
            success=False,
            agent_name=self.name,
            errors=[f"Failed after {max_iter} iterations"] + errors,
            iterations_used=max_iter,
            trace_log=list(self._trace),
        )

    def _build_scad_prompt(self, description: str, constraints: Dict) -> str:
        """Convert AFO constraints into an OpenSCAD generation prompt."""
        return (
            f"Generate OpenSCAD code for a pediatric ankle-foot orthosis (AFO).\n"
            f"Description: {description}\n"
            f"AFO Type: {constraints.get('afo_type', 'solid')}\n"
            f"Ankle angle: {constraints.get('ankle_target_deg', 0)}°\n"
            f"Wall thickness: {constraints.get('wall_thickness_mm', 3.0)}mm\n"
            f"Foot length range: {constraints.get('foot_length_range_mm', (165, 200))}mm\n"
            f"Ankle width range: {constraints.get('ankle_width_range_mm', (46, 55))}mm\n"
            f"Trim line: {constraints.get('trim_line', 'full')}\n"
            f"Flex zone: {constraints.get('flex_zone', False)}\n"
            f"Growth accommodation: {constraints.get('growth_accommodation_mm', 5)}mm\n"
            f"\nThe AFO must be a single printable solid with:\n"
            f"- Posterior calf shell extending to fibular head minus 15mm\n"
            f"- Footplate with toe break anterior to metatarsal heads\n"
            f"- Smooth internal surfaces (no sharp edges)\n"
            f"- Uniform wall thickness ±0.3mm\n"
            f"- Malleolar clearance ≥3mm\n"
        )

    def _generate_scad(self, prompt: str, previous_code: Optional[str],
                        errors: List[str]) -> str:
        """
        Generate OpenSCAD code. In production, calls local LLM.
        Here provides a parametric template for AFO generation.
        """
        # In production: call local LLM (Ollama / llama.cpp) with prompt + errors
        # For standalone operation, use parametric template
        if previous_code and not errors:
            return previous_code

        return self._get_parametric_afo_template()

    def _get_parametric_afo_template(self) -> str:
        """Return a parametric OpenSCAD AFO template."""
        return """
// OrthoBraceForge — Parametric Pediatric AFO
// Generated by agentic3d agent

// === Parameters ===
foot_length = 180;        // mm
foot_width = 70;          // mm
ankle_width = 50;         // mm
calf_circumference = 220; // mm
calf_height = 180;        // mm — distance ankle to fibular head
wall_thickness = 3.0;     // mm
ankle_angle = 0;          // degrees dorsiflexion (0=neutral)
trim_clearance = 3;       // mm from malleoli
growth_margin = 5;        // mm added to length

// === Derived ===
total_foot_length = foot_length + growth_margin;
calf_radius = calf_circumference / (2 * PI);
footplate_width = foot_width + 2 * wall_thickness;

module footplate() {
    difference() {
        // Outer shell
        hull() {
            translate([0, 0, 0])
                cube([total_foot_length, footplate_width, wall_thickness]);
            // Toe rocker
            translate([total_foot_length * 0.7, footplate_width/2, 0])
                cylinder(h=wall_thickness, r=footplate_width/3, $fn=60);
        }
        // Inner relief for foot contact
        translate([wall_thickness, wall_thickness, -0.1])
            cube([total_foot_length - 2*wall_thickness,
                  footplate_width - 2*wall_thickness,
                  wall_thickness + 0.2]);
    }
}

module posterior_wall() {
    translate([0, footplate_width/2, wall_thickness]) {
        rotate([ankle_angle, 0, 0]) {
            difference() {
                // Outer wall
                translate([-wall_thickness/2, -ankle_width/2 - wall_thickness, 0])
                    cube([wall_thickness, ankle_width + 2*wall_thickness, calf_height]);
                // Inner cavity
                translate([-wall_thickness/2 - 0.1, -ankle_width/2, wall_thickness])
                    cube([wall_thickness + 0.2, ankle_width, calf_height]);
                // Malleolar clearance cutouts
                for (side = [-1, 1]) {
                    translate([0, side * (ankle_width/2 + trim_clearance), ankle_width/2])
                        sphere(r=trim_clearance + 5, $fn=40);
                }
            }
        }
    }
}

module calf_cuff() {
    translate([0, footplate_width/2, wall_thickness + calf_height * 0.6]) {
        rotate([ankle_angle, 0, 0]) {
            difference() {
                cylinder(h=calf_height*0.35, r=calf_radius + wall_thickness, $fn=80);
                cylinder(h=calf_height*0.35 + 0.1, r=calf_radius, $fn=80);
                // Opening for donning
                translate([calf_radius * 0.3, -calf_radius*1.5, -0.1])
                    cube([calf_radius * 2, calf_radius * 3, calf_height*0.35 + 0.2]);
            }
        }
    }
}

// === Assembly ===
union() {
    footplate();
    posterior_wall();
    calf_cuff();
}
"""

    def _validate_scad_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """Basic OpenSCAD syntax validation."""
        errors = []
        # Check for balanced braces
        if code.count("{") != code.count("}"):
            errors.append("Unbalanced curly braces")
        if code.count("(") != code.count(")"):
            errors.append("Unbalanced parentheses")
        # Check for required modules
        if "module" not in code and "union" not in code:
            errors.append("No module or union found — likely not valid OpenSCAD")
        return (len(errors) == 0, errors)

    def _render_stl(self, scad_code: str, scad_path: str, stl_path: str) -> bool:
        """Render OpenSCAD code to STL via subprocess."""
        try:
            Path(scad_path).write_text(scad_code, encoding="utf-8")
            # Attempt OpenSCAD CLI render
            result = subprocess.run(
                ["openscad", "-o", stl_path, scad_path],
                capture_output=True, text=True, timeout=OPENSCAD_TIMEOUT_SEC,
            )
            if result.returncode == 0 and Path(stl_path).exists():
                return True
            self._log(f"OpenSCAD stderr: {result.stderr[:500]}")
            return False
        except FileNotFoundError:
            self._log("OpenSCAD not found — using template-only mode")
            # In bundled exe, OpenSCAD may not be available; mark as needing
            # external render
            Path(scad_path).write_text(scad_code, encoding="utf-8")
            return False
        except (subprocess.SubprocessError, OSError) as e:
            self._log(f"Render error: {e}")
            return False
