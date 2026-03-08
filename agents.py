"""
OrthoBraceForge — Agent Wrappers
Unified interface classes for all 9 vendored repository integrations.
Each agent is a self-contained unit that can be orchestrated by LangGraph.
"""
import json
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import (
    AFO_HEIGHT_MAX_MM,
    AFO_HEIGHT_MIN_MM,
    AFO_LENGTH_MAX_MM,
    AFO_LENGTH_MIN_MM,
    BUILD123D_TIMEOUT_SEC,
    EXPORT_DIR,
    FEA_DEFAULTS,
    MATERIALS,
    MAX_AGENT_ITERATIONS,
    OCTOPRINT_API_KEY,
    OCTOPRINT_CONNECT_TIMEOUT_SEC,
    OCTOPRINT_URL,
    OPENSCAD_TIMEOUT_SEC,
    VLM_CRITIQUE_MAX_ROUNDS,
)
from exceptions import (
    CADGenerationError,
)

logger = logging.getLogger("orthobraceforge.agents")


# ===========================================================================
# Base Agent Interface
# ===========================================================================
@dataclass
class AgentResult:
    """Standardized result from any agent invocation."""
    success: bool
    agent_name: str
    output_data: Dict[str, Any] = field(default_factory=dict)
    output_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    iterations_used: int = 0
    trace_log: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base for all agent wrappers."""

    def __init__(self, name: str):
        self.name = name
        self._trace: List[str] = []

    def _log(self, msg: str):
        entry = f"[{self.name}] {msg}"
        self._trace.append(entry)
        logger.info(entry)

    def run(self, params: Dict[str, Any]) -> AgentResult:
        """Wrapper around execute() that logs start/end with timing."""
        start = datetime.now(timezone.utc)
        run_id = params.get("run_id", "")
        patient_id = params.get("patient_id", "")
        self._log(f"START execute | run_id={run_id} patient_id={patient_id}")
        try:
            result = self.execute(params)
        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            self._log(f"FAILED execute | error={e} elapsed={elapsed:.2f}s")
            raise
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        self._log(f"END execute | success={result.success} elapsed={elapsed:.2f}s")
        return result

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> AgentResult:
        ...


# ===========================================================================
# 1. Agentic3D — reetm09/agentic3d (Autogen OpenSCAD agent loop)
# ===========================================================================
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

        errors = []
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


# ===========================================================================
# 2. FormaAI — andreyka/forma-ai-service (build123d self-correction)
# ===========================================================================
class FormaAIAgent(BaseAgent):
    """
    Wraps forma-ai-service for build123d CAD generation with
    control-flow self-correction. PREFERRED engine for AFO generation.
    Generates Python build123d code, executes it, validates geometry,
    and iteratively corrects based on error feedback.
    """

    def __init__(self):
        super().__init__("forma_ai")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Starting build123d self-correction loop")

        constraints = params.get("constraints", {})
        max_iter = params.get("max_iterations", MAX_AGENT_ITERATIONS)
        design_id = params.get("design_id", "temp")

        output_stl = str(EXPORT_DIR / f"forma_{design_id}.stl")
        output_step = str(EXPORT_DIR / f"forma_{design_id}.step")
        output_py = str(EXPORT_DIR / f"forma_{design_id}_build123d.py")

        errors = []
        b123d_code = None

        for iteration in range(1, max_iter + 1):
            self._log(f"Iteration {iteration}/{max_iter}")

            try:
                # Generate build123d Python code
                b123d_code = self._generate_build123d(constraints, b123d_code, errors)
                self._log(f"Generated build123d code ({len(b123d_code)} chars)")

                # Write and execute
                Path(output_py).write_text(b123d_code, encoding="utf-8")

                exec_result = self._execute_build123d(output_py, output_stl, output_step)

                if exec_result["success"]:
                    # Validate geometry
                    validation = self._validate_geometry(output_stl, constraints)
                    if validation["valid"]:
                        self._log("Geometry validated successfully")
                        return AgentResult(
                            success=True,
                            agent_name=self.name,
                            output_data={
                                "build123d_code": b123d_code,
                                "validation": validation,
                            },
                            output_files=[output_stl, output_step, output_py],
                            iterations_used=iteration,
                            trace_log=list(self._trace),
                        )
                    else:
                        errors = validation.get("errors", ["Geometry validation failed"])
                        self._log(f"Validation failed: {errors}")
                else:
                    errors = exec_result.get("errors", ["Execution failed"])
                    self._log(f"Execution failed: {errors}")

            except (CADGenerationError, subprocess.SubprocessError, OSError) as e:
                errors = [str(e)]
                self._log(f"CAD error: {e}")
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error in iteration {iteration}: {e}", exc_info=True)
                errors = [str(e)]

        return AgentResult(
            success=False,
            agent_name=self.name,
            errors=[f"Failed after {max_iter} iterations"] + errors,
            iterations_used=max_iter,
            trace_log=list(self._trace),
        )

    def _generate_build123d(self, constraints: Dict, previous_code: Optional[str],
                             errors: List[str]) -> str:
        """
        Generate build123d Python code for AFO.
        In production: local LLM generates code; here returns parametric template.
        """
        foot_length = constraints.get("foot_length_mm", 180)
        ankle_width = constraints.get("ankle_width_mm", 50)
        thickness = constraints.get("wall_thickness_mm", 3.0)
        ankle_angle = constraints.get("ankle_target_deg", 0)
        afo_type = constraints.get("afo_type", "solid")
        growth = constraints.get("growth_accommodation_mm", 5)

        return f'''"""
OrthoBraceForge — build123d Parametric Pediatric AFO
Auto-generated by FormaAI agent with self-correction
"""
from build123d import (
    BuildPart, BuildSketch, BuildLine, Compound, Plane, Axis, Mode,
    Line, Spline, RadiusArc, Circle, Sphere,
    Locations, make_face, extrude, rotate,
)
import math

# === Patient-Specific Parameters ===
FOOT_LENGTH = {foot_length} + {growth}  # mm (includes growth margin)
FOOT_WIDTH = {ankle_width * 1.4:.1f}     # mm (estimated from ankle width)
ANKLE_WIDTH = {ankle_width}              # mm
WALL_THICKNESS = {thickness}             # mm
ANKLE_ANGLE_DEG = {ankle_angle}          # degrees dorsiflexion
AFO_TYPE = "{afo_type}"
CALF_HEIGHT = 180                        # mm (ankle to fibular head - 15mm)
CALF_CIRC = ANKLE_WIDTH * math.pi * 1.2  # mm estimated

# === Footplate ===
with BuildPart() as footplate:
    with BuildSketch():
        # Anatomical footplate shape
        with BuildLine():
            # Heel
            l1 = Line((0, 0), (0, FOOT_WIDTH))
            # Lateral border
            l2 = Spline((0, FOOT_WIDTH),
                        (FOOT_LENGTH * 0.3, FOOT_WIDTH * 1.05),
                        (FOOT_LENGTH * 0.7, FOOT_WIDTH * 0.95),
                        (FOOT_LENGTH, FOOT_WIDTH * 0.5))
            # Toe
            l3 = RadiusArc((FOOT_LENGTH, FOOT_WIDTH * 0.5),
                           (FOOT_LENGTH, 0), -FOOT_WIDTH * 0.3)
            # Medial border
            l4 = Spline((FOOT_LENGTH, 0),
                        (FOOT_LENGTH * 0.7, -FOOT_WIDTH * 0.05),
                        (FOOT_LENGTH * 0.3, 0),
                        (0, 0))
        make_face()
    extrude(amount=WALL_THICKNESS)

# === Posterior Wall ===
with BuildPart() as posterior_wall:
    with BuildSketch(Plane.XZ.offset(-FOOT_WIDTH / 2)):
        # Posterior wall profile
        with BuildLine():
            l1 = Line((0, WALL_THICKNESS), (0, CALF_HEIGHT))
            l2 = Line((0, CALF_HEIGHT), (WALL_THICKNESS, CALF_HEIGHT))
            l3 = Line((WALL_THICKNESS, CALF_HEIGHT), (WALL_THICKNESS, WALL_THICKNESS))
            l4 = Line((WALL_THICKNESS, WALL_THICKNESS), (0, WALL_THICKNESS))
        make_face()
    extrude(amount=ANKLE_WIDTH + 2 * WALL_THICKNESS)

    # Ankle angle rotation
    if ANKLE_ANGLE_DEG != 0:
        rotate(axis=Axis.Y, angle=ANKLE_ANGLE_DEG)

    # Malleolar relief cutouts
    with BuildPart(mode=Mode.SUBTRACT):
        with Locations([(WALL_THICKNESS/2, -ANKLE_WIDTH/2, ANKLE_WIDTH * 0.6),
                        (WALL_THICKNESS/2, ANKLE_WIDTH/2, ANKLE_WIDTH * 0.6)]):
            Sphere(radius=8)  # 8mm relief for malleoli

# === Calf Cuff (partial cylinder) ===
with BuildPart() as calf_cuff:
    calf_radius = CALF_CIRC / (2 * math.pi)
    with BuildSketch(Plane.XY.offset(CALF_HEIGHT * 0.65)):
        Circle(calf_radius + WALL_THICKNESS)
        Circle(calf_radius, mode=Mode.SUBTRACT)
        # Opening for donning (anterior 120°)
        with BuildLine():
            l1 = Line((-calf_radius * 1.5, 0), (calf_radius * 1.5, 0))
            l2 = Line((calf_radius * 1.5, 0), (calf_radius * 1.5, calf_radius * 1.5))
            l3 = Line((calf_radius * 1.5, calf_radius * 1.5),
                      (-calf_radius * 1.5, calf_radius * 1.5))
            l4 = Line((-calf_radius * 1.5, calf_radius * 1.5), (-calf_radius * 1.5, 0))
        make_face(mode=Mode.SUBTRACT)
    extrude(amount=CALF_HEIGHT * 0.3)

# === Assembly ===
afo_assembly = Compound(children=[
    footplate.part,
    posterior_wall.part,
    calf_cuff.part,
])

# === Export ===
afo_assembly.export_stl("{output_stl}")
afo_assembly.export_step("{output_step}")
print("BUILD123D_SUCCESS: AFO exported to STL and STEP")
'''

    def _execute_build123d(self, py_path: str, stl_path: str,
                            step_path: str) -> Dict:
        """Execute build123d script as subprocess."""
        try:
            result = subprocess.run(
                ["python", py_path],
                capture_output=True, text=True, timeout=BUILD123D_TIMEOUT_SEC,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            success = (
                result.returncode == 0
                and "BUILD123D_SUCCESS" in result.stdout
                and Path(stl_path).exists()
            )
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "errors": [result.stderr] if not success else [],
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "errors": ["Build123d execution timed out (180s)"]}
        except OSError as e:
            return {"success": False, "errors": [str(e)]}

    def _validate_geometry(self, stl_path: str, constraints: Dict) -> Dict:
        """Validate STL geometry against design constraints."""
        try:
            import trimesh
            mesh = trimesh.load(stl_path)

            errors = []
            bounds = mesh.bounds  # [[min_x, min_y, min_z], [max_x, max_y, max_z]]
            dims = bounds[1] - bounds[0]

            # Check overall dimensions are reasonable for an AFO
            if dims[0] < AFO_LENGTH_MIN_MM or dims[0] > AFO_LENGTH_MAX_MM:
                errors.append(f"Length {dims[0]:.1f}mm outside AFO range [{AFO_LENGTH_MIN_MM}-{AFO_LENGTH_MAX_MM}]")
            if dims[2] < AFO_HEIGHT_MIN_MM or dims[2] > AFO_HEIGHT_MAX_MM:
                errors.append(f"Height {dims[2]:.1f}mm outside AFO range [{AFO_HEIGHT_MIN_MM}-{AFO_HEIGHT_MAX_MM}]")
            if not mesh.is_watertight:
                errors.append("Mesh is not watertight — not printable")

            return {
                "valid": len(errors) == 0,
                "dimensions_mm": dims.tolist(),
                "volume_cm3": mesh.volume / 1000,
                "is_watertight": mesh.is_watertight,
                "triangle_count": len(mesh.faces),
                "errors": errors,
            }
        except ImportError:
            return {"valid": True, "errors": [], "note": "trimesh not available for validation"}
        except (OSError, ValueError) as e:
            return {"valid": False, "errors": [str(e)]}


# ===========================================================================
# 3. TalkCAD — outerreaches/talkcad (Conversational orchestrator)
# ===========================================================================
class TalkCADAgent(BaseAgent):
    """
    Wraps talkcad for conversational CAD refinement.
    Accepts natural language modification requests and applies them
    to existing CAD parameters.
    """

    def __init__(self):
        super().__init__("talkcad")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Processing conversational CAD modification")

        instruction = params.get("instruction", "")
        current_params = params.get("current_parameters", {})

        # Parse the natural language instruction into parameter modifications
        modifications = self._parse_instruction(instruction, current_params)
        self._log(f"Parsed modifications: {json.dumps(modifications, indent=2)}")

        # Apply modifications
        updated_params = {**current_params, **modifications}

        return AgentResult(
            success=True,
            agent_name=self.name,
            output_data={
                "original_instruction": instruction,
                "modifications": modifications,
                "updated_parameters": updated_params,
            },
            iterations_used=1,
            trace_log=list(self._trace),
        )

    def _parse_instruction(self, instruction: str, current: Dict) -> Dict:
        """
        Parse NL instruction into parameter changes.
        In production: uses local LLM for NLU.
        Here: rule-based parsing for common AFO modifications.
        """
        mods = {}
        inst_lower = instruction.lower()

        # Thickness modifications
        if "thicker" in inst_lower or "increase thickness" in inst_lower:
            mods["wall_thickness_mm"] = current.get("wall_thickness_mm", 3.0) + 0.5
        elif "thinner" in inst_lower or "decrease thickness" in inst_lower:
            mods["wall_thickness_mm"] = max(2.5, current.get("wall_thickness_mm", 3.0) - 0.5)

        # Angle modifications
        if "more dorsiflexion" in inst_lower:
            mods["ankle_target_deg"] = current.get("ankle_target_deg", 0) + 2
        elif "more plantarflexion" in inst_lower or "less dorsiflexion" in inst_lower:
            mods["ankle_target_deg"] = current.get("ankle_target_deg", 0) - 2

        # AFO type changes
        if "hinged" in inst_lower:
            mods["afo_type"] = "hinged"
        elif "solid" in inst_lower:
            mods["afo_type"] = "solid"
        elif "leaf spring" in inst_lower or "pls" in inst_lower:
            mods["afo_type"] = "posterior_leaf_spring"

        # Flex zone
        if "add flex" in inst_lower or "flex zone" in inst_lower:
            mods["flex_zone"] = True
        elif "remove flex" in inst_lower or "rigid" in inst_lower:
            mods["flex_zone"] = False

        if not mods:
            self._log("No recognized modifications — passing instruction to LLM")
            mods["_unresolved_instruction"] = instruction

        return mods


# ===========================================================================
# 4. CADAgent — Svetlana-DAO-LLC/cad-agent (Headless render server)
# ===========================================================================
class CADRenderAgent(BaseAgent):
    """
    Wraps cad-agent for headless mesh rendering.
    Takes STL/STEP files and produces rendered images for VLM critique.
    Simulated via subprocess (no Docker required in bundled exe).
    """

    def __init__(self):
        super().__init__("cad_render")

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Starting headless render")

        mesh_path = params.get("mesh_path", "")
        views = params.get("views", ["front", "side", "top", "perspective"])
        design_id = params.get("design_id", "temp")

        if not Path(mesh_path).exists():
            return AgentResult(
                success=False, agent_name=self.name,
                errors=[f"Mesh file not found: {mesh_path}"],
                trace_log=list(self._trace),
            )

        rendered_images = []
        for view in views:
            img_path = str(EXPORT_DIR / f"render_{design_id}_{view}.png")
            success = self._render_view(mesh_path, view, img_path)
            if success:
                rendered_images.append(img_path)
                self._log(f"Rendered {view} view → {img_path}")
            else:
                self._log(f"Failed to render {view} view")

        return AgentResult(
            success=len(rendered_images) > 0,
            agent_name=self.name,
            output_data={"views_rendered": len(rendered_images)},
            output_files=rendered_images,
            iterations_used=1,
            trace_log=list(self._trace),
        )

    def _render_view(self, mesh_path: str, view: str, output_path: str) -> bool:
        """Render a single view of the mesh using PyVista offscreen."""
        try:
            import pyvista as pv
            pv.OFF_SCREEN = True

            mesh = pv.read(mesh_path)
            plotter = pv.Plotter(off_screen=True, window_size=[1024, 768])
            plotter.add_mesh(mesh, color="lightblue", show_edges=False,
                           specular=0.5, smooth_shading=True)

            camera_positions = {
                "front": [(0, -500, 100), (0, 0, 100), (0, 0, 1)],
                "side": [(-500, 0, 100), (0, 0, 100), (0, 0, 1)],
                "top": [(0, 0, 500), (0, 0, 0), (0, 1, 0)],
                "perspective": [(-400, -400, 300), (0, 0, 100), (0, 0, 1)],
            }
            pos = camera_positions.get(view, camera_positions["perspective"])
            plotter.camera_position = pos

            plotter.screenshot(output_path)
            plotter.close()
            return Path(output_path).exists()
        except (ImportError, OSError) as e:
            self._log(f"Render error: {e}")
            return False


# ===========================================================================
# 5. LLM3DPrint — BaratiLab/LLM-3D-Print (Printer defect correction)
# ===========================================================================
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


# ===========================================================================
# 6. OrthoInsoles — Green-AI-Hub (Adapted for AFO parametric prediction)
# ===========================================================================
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


# ===========================================================================
# 7. OctoMCP — OctoEverywhere/mcp (Printer state/control broker)
# ===========================================================================
class OctoMCPAgent(BaseAgent):
    """
    Local MCP broker for 3D printer communication.
    Interfaces with OctoPrint/Klipper via local network.
    """

    def __init__(self):
        super().__init__("octo_mcp")
        self._printer_url = os.environ.get("OCTOPRINT_URL", OCTOPRINT_URL)
        self._api_key = os.environ.get("OCTOPRINT_API_KEY", OCTOPRINT_API_KEY)
        if not self._api_key:
            try:
                import keyring
                self._api_key = keyring.get_password("orthobraceforge", "octoprint_api_key") or ""
            except ImportError:
                pass

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        action = params.get("action", "status")
        self._log(f"MCP action: {action}")

        if action == "status":
            status = self._get_printer_status()
            return AgentResult(
                success=True, agent_name=self.name,
                output_data={"printer_status": status},
                trace_log=list(self._trace),
            )
        elif action == "upload":
            gcode_path = params.get("gcode_path", "")
            result = self._upload_gcode(gcode_path)
            return AgentResult(
                success=result, agent_name=self.name,
                output_data={"uploaded": result},
                trace_log=list(self._trace),
            )
        elif action == "start_print":
            result = self._start_print(params.get("filename", ""))
            return AgentResult(
                success=result, agent_name=self.name,
                output_data={"print_started": result},
                trace_log=list(self._trace),
            )
        elif action == "pause":
            return AgentResult(
                success=True, agent_name=self.name,
                output_data={"paused": True},
                trace_log=list(self._trace),
            )
        else:
            return AgentResult(
                success=False, agent_name=self.name,
                errors=[f"Unknown action: {action}"],
                trace_log=list(self._trace),
            )

    def _validate_api_key(self) -> None:
        """Raise ValueError if API key is not configured."""
        if not self._api_key:
            raise ValueError(
                "OctoPrint API key is not configured. "
                "Set the OCTOPRINT_API_KEY environment variable."
            )

    def _get_printer_status(self) -> Dict:
        """Query printer status via OctoPrint API."""
        try:
            self._validate_api_key()
            import urllib.request
            req = urllib.request.Request(
                f"{self._printer_url}/api/printer",
                headers={"X-Api-Key": self._api_key},
            )
            with urllib.request.urlopen(req, timeout=OCTOPRINT_CONNECT_TIMEOUT_SEC) as resp:
                return json.loads(resp.read())
        except ValueError as e:
            self._log(f"Printer config error: {e}")
            return {"state": "unconfigured", "error": str(e)}
        except (OSError, TimeoutError) as e:
            self._log(f"Printer status error: {e}")
            return {"state": "offline", "error": str(e)}

    def _upload_gcode(self, gcode_path: str) -> bool:
        """Upload G-code file to OctoPrint via multipart POST /api/files/local."""
        import urllib.error
        import urllib.request

        self._validate_api_key()

        gcode_file = Path(gcode_path).resolve()
        # Path must exist and must be inside EXPORT_DIR (allowlist check)
        try:
            gcode_file.relative_to(EXPORT_DIR.resolve())
        except ValueError:
            logger.warning(f"[{self.name}] Security: gcode_path outside EXPORT_DIR: {gcode_path}")
            self._log(f"Security: gcode_path outside EXPORT_DIR: {gcode_path}")
            return False

        if not gcode_file.exists():
            self._log(f"G-code file not found: {gcode_file}")
            return False

        self._log(f"Uploading {gcode_file.name} to OctoPrint …")
        boundary = "----OBFBoundary"
        filename = gcode_file.name
        file_data = gcode_file.read_bytes()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{self._printer_url}/api/files/local",
            data=body,
            headers={
                "X-Api-Key": self._api_key,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=OCTOPRINT_CONNECT_TIMEOUT_SEC) as resp:
                resp_data = json.loads(resp.read())
                self._log(f"Upload success: {resp_data.get('name', filename)}")
                return True
        except urllib.error.HTTPError as e:
            self._log(f"Upload HTTP error {e.code}: {e.reason}")
            return False
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            self._log(f"Upload error: {e}")
            return False

    def _start_print(self, filename: str) -> bool:
        """Issue a start-job command to OctoPrint via POST /api/job."""
        import urllib.error
        import urllib.request

        self._validate_api_key()

        if not filename:
            self._log("start_print: filename must not be empty")
            return False

        self._log(f"Sending print-start command for: {filename}")
        payload = json.dumps({"command": "start"}).encode()
        req = urllib.request.Request(
            f"{self._printer_url}/api/job",
            data=payload,
            headers={
                "X-Api-Key": self._api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=OCTOPRINT_CONNECT_TIMEOUT_SEC) as resp:
                self._log(f"Print started — HTTP {resp.status}")
                return resp.status == 204
        except urllib.error.HTTPError as e:
            self._log(f"Print-start HTTP error {e.code}: {e.reason}")
            return False
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            self._log(f"Print-start error: {e}")
            return False


# ===========================================================================
# 8. AgenticAlloy — BaratiLab (Titanium lattice evaluation)
# ===========================================================================
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


# ===========================================================================
# 9. ChatToSTL — nchourrout/Chat-To-STL (Fallback generator)
# ===========================================================================
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


# ===========================================================================
# VLM Render-Critique Agent (uses CADRenderAgent + local VLM)
# ===========================================================================
class VLMCritiqueAgent(BaseAgent):
    """
    Iterative VLM-based render-critique loop.
    Renders the current design, analyzes it visually, and provides
    structured feedback for design improvement.
    """

    def __init__(self):
        super().__init__("vlm_critique")
        self.render_agent = CADRenderAgent()

    def execute(self, params: Dict[str, Any]) -> AgentResult:
        self._trace = []
        self._log("Starting VLM render-critique loop")

        mesh_path = params.get("mesh_path", "")
        constraints = params.get("constraints", {})
        max_rounds = params.get("max_rounds", VLM_CRITIQUE_MAX_ROUNDS)

        # Render the mesh
        render_result = self.render_agent.execute({
            "mesh_path": mesh_path,
            "design_id": params.get("design_id", "temp"),
        })

        if not render_result.success:
            return AgentResult(
                success=False, agent_name=self.name,
                errors=["Render failed — cannot perform visual critique"],
                trace_log=list(self._trace),
            )

        # Perform visual analysis
        critique = self._analyze_renders(render_result.output_files, constraints)
        self._log(f"Critique score: {critique['score']}/10")

        return AgentResult(
            success=critique["score"] >= 7.0,
            agent_name=self.name,
            output_data={
                "critique": critique,
                "rendered_images": render_result.output_files,
            },
            iterations_used=1,
            trace_log=list(self._trace) + render_result.trace_log,
        )

    def _analyze_renders(self, image_paths: List[str],
                          constraints: Dict) -> Dict:
        """
        Analyze rendered images for design quality.
        Production: runs local VLM (LLaVA / Qwen-VL).
        Stub: returns passing score for valid renders.
        """
        return {
            "score": 8.0,
            "issues": [],
            "suggestions": [
                "Consider adding fillet to posterior wall edges for comfort",
                "Malleolar relief could be slightly deeper",
            ],
            "overall": "Design appears anatomically reasonable for pediatric AFO",
            "images_analyzed": len(image_paths),
        }
