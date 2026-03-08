"""
OrthoBraceForge — CAD Render Agent
Wraps Svetlana-DAO-LLC/cad-agent (Headless render server).
"""
from pathlib import Path
from typing import Any, Dict

from config import EXPORT_DIR

from .base import AgentResult, BaseAgent


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
