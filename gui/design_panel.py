"""
OrthoBraceForge — Design Panel Screens
Screen 3: Preview3DScreen — interactive PyVista mesh viewer.
Screen 4: GenerationProgressScreen — live pipeline progress + agent trace.
Screen 5: ComplianceReportScreen — compliance check results and audit report.
"""
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import APP_CLASSIFICATION


# ===========================================================================
# Screen 3: 3D Preview (PyVista Embedded)
# ===========================================================================
class Preview3DScreen(QWidget):
    """Interactive 3D mesh preview with PyVista embedded in Qt."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("3D Design Preview")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # PyVista widget placeholder
        self.preview_container = QWidget()
        self.preview_container.setMinimumSize(600, 400)
        self.preview_container.setStyleSheet(
            "background-color: #0a0a1a; border: 1px solid #333366; border-radius: 4px;"
        )

        # Placeholder label until mesh is loaded
        self.placeholder = QLabel("No design loaded.\nGenerate an AFO to preview.")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: #555; font-size: 14px;")
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.addWidget(self.placeholder)

        layout.addWidget(self.preview_container, 1)

        # Controls
        ctrl_row = QHBoxLayout()
        self.reset_btn = QPushButton("Reset View")
        self.wireframe_btn = QPushButton("Toggle Wireframe")
        self.screenshot_btn = QPushButton("Screenshot")
        ctrl_row.addWidget(self.reset_btn)
        ctrl_row.addWidget(self.wireframe_btn)
        ctrl_row.addWidget(self.screenshot_btn)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Mesh info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.info_label)

    def load_mesh(self, stl_path: str):
        """Load and display STL mesh in the PyVista viewer."""
        try:
            import pyvista as pv
            from pyvistaqt import QtInteractor

            # Remove placeholder
            self.placeholder.hide()

            # Create PyVista interactor
            if hasattr(self, '_plotter'):
                self._plotter.close()

            layout = self.preview_container.layout()
            self._plotter = QtInteractor(self.preview_container)
            layout.addWidget(self._plotter.interactor)

            mesh = pv.read(stl_path)
            self._plotter.add_mesh(
                mesh, color="#5dade2", show_edges=False,
                smooth_shading=True, specular=0.5,
            )
            self._plotter.add_axes()
            self._plotter.reset_camera()

            bounds = mesh.bounds
            dims = [bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4]]
            self.info_label.setText(
                f"Dimensions: {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} mm | "
                f"Triangles: {mesh.n_faces:,} | "
                f"Volume: {mesh.volume/1000:.1f} cm³ | "
                f"Watertight: {'Yes' if mesh.is_manifold else 'No'}"
            )

            # Connect controls
            self.reset_btn.clicked.connect(self._plotter.reset_camera)
            self.screenshot_btn.clicked.connect(
                lambda: self._plotter.screenshot(
                    str(Path.home() / "orthobraceforge_screenshot.png")
                )
            )

        except ImportError:
            self.placeholder.setText(
                "PyVista/VTK not available.\n"
                "STL file saved — open in external viewer."
            )
            self.info_label.setText(f"STL path: {stl_path}")
        except Exception as e:
            self.placeholder.setText(f"Preview error: {e}")


# ===========================================================================
# Screen 4: Generation Progress + Agent Trace
# ===========================================================================
class GenerationProgressScreen(QWidget):
    """Live pipeline progress with agent trace log."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Design Generation Pipeline")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Phase indicator
        self.phase_label = QLabel("Phase: Initializing…")
        self.phase_label.setStyleSheet("color: #5dade2; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.phase_label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 11)  # 11 phases
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Phase status grid
        self.phase_statuses = {}
        phases = [
            "intake", "compliance", "parametric", "cad_generation",
            "render", "vlm_critique", "fea_analysis", "lattice_eval",
            "human_review", "export", "print",
        ]
        status_grid = QGridLayout()
        for idx, phase in enumerate(phases):
            label = QLabel(f"● {phase.replace('_', ' ').title()}")
            label.setStyleSheet("color: #555; font-size: 11px;")
            self.phase_statuses[phase] = label
            row, col = divmod(idx, 3)
            status_grid.addWidget(label, row, col)
        layout.addLayout(status_grid)

        # Agent trace log
        trace_group = QGroupBox("Agent Trace Log")
        trace_layout = QVBoxLayout()
        self.trace_log = QPlainTextEdit()
        self.trace_log.setReadOnly(True)
        self.trace_log.setMaximumBlockCount(2000)
        trace_layout.addWidget(self.trace_log)
        trace_group.setLayout(trace_layout)
        layout.addWidget(trace_group, 1)

        # Warnings / Errors
        self.warnings_label = QLabel("")
        self.warnings_label.setWordWrap(True)
        self.warnings_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        layout.addWidget(self.warnings_label)

    def update_phase(self, phase: str, state: dict = None):
        """Update the progress display for a new phase."""
        phase_order = [
            "intake", "compliance", "parametric", "cad_generation",
            "render", "vlm_critique", "fea_analysis", "lattice_eval",
            "human_review", "export", "print", "complete",
        ]
        idx = phase_order.index(phase) if phase in phase_order else 0
        self.progress.setValue(idx)
        self.phase_label.setText(f"Phase: {phase.replace('_', ' ').title()}")

        # Update status indicators
        for p, label in self.phase_statuses.items():
            p_idx = phase_order.index(p) if p in phase_order else 99
            if p_idx < idx:
                label.setStyleSheet("color: #27ae60; font-size: 11px;")  # Complete
            elif p_idx == idx:
                label.setStyleSheet("color: #5dade2; font-size: 11px; font-weight: bold;")
            else:
                label.setStyleSheet("color: #555; font-size: 11px;")

    def append_trace(self, message: str):
        """Append a message to the trace log."""
        self.trace_log.appendPlainText(message)

    def show_warnings(self, warnings: List[str]):
        if warnings:
            self.warnings_label.setText("⚠ " + " | ".join(warnings[-3:]))


# ===========================================================================
# Screen 5: Compliance / Audit Report
# ===========================================================================
class ComplianceReportScreen(QWidget):
    """Displays compliance check results and audit report."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Compliance & Audit Report")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        banner = QLabel(APP_CLASSIFICATION)
        banner.setObjectName("banner")
        layout.addWidget(banner)

        # Report content
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout.addWidget(self.report_text, 1)

        # Export button
        btn_row = QHBoxLayout()
        self.export_pdf_btn = QPushButton("Export Audit PDF")
        self.export_pdf_btn.setObjectName("primaryBtn")
        btn_row.addWidget(self.export_pdf_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def load_report(self, state: dict):
        """Populate the report from pipeline state."""
        html = "<style>body{color:#e0e0e0;font-family:Segoe UI;}"
        html += "h2{color:#5dade2;} .pass{color:#27ae60;} .fail{color:#e74c3c;}"
        html += ".warn{color:#f39c12;} table{border-collapse:collapse;width:100%;}"
        html += "td,th{padding:4px 8px;border:1px solid #333;text-align:left;}"
        html += "</style>"

        compliance = state.get("compliance_result", {})
        passed = compliance.get("passed", False)

        html += f"<h2>Compliance Status: <span class='{'pass' if passed else 'fail'}'>"
        html += f"{'PASSED' if passed else 'FAILED'}</span></h2>"

        html += "<h3>Regulatory Flags</h3><ul>"
        for flag in state.get("regulatory_flags", []):
            html += f"<li>{flag}</li>"
        html += "</ul>"

        for issue in compliance.get("blocking_issues", []):
            html += f"<p class='fail'>BLOCKING: {issue}</p>"
        for warn in compliance.get("warnings", []):
            html += f"<p class='warn'>Warning: {warn}</p>"

        # FEA summary
        fea = state.get("fea_result", {})
        if fea:
            fea_pass = fea.get("passed", False)
            html += f"<h2>FEA Analysis: <span class='{'pass' if fea_pass else 'fail'}'>"
            html += f"{'PASSED' if fea_pass else 'FAILED'}</span></h2>"
            html += "<table>"

            # Safety factor with color coding
            sf = fea.get("safety_factor", 0)
            req_sf = fea.get("required_safety_factor", 3.0)
            sf_class = "pass" if sf >= req_sf else "fail"
            html += (f"<tr><td><b>Safety Factor</b></td>"
                     f"<td><span class='{sf_class}'><b>{sf}</b></span>"
                     f" (required: {req_sf})</td></tr>")

            fea_fields = [
                ("Max Von Mises Stress", "max_von_mises_mpa", " MPa"),
                ("% of Yield Strength", "von_mises_pct_yield", "%"),
                ("Dynamic Load", "dynamic_load_n", " N"),
                ("Material", "material", ""),
                ("Analysis Method", "method", ""),
            ]
            for label, key, unit in fea_fields:
                val = fea.get(key)
                if val is not None:
                    html += f"<tr><td><b>{label}</b></td><td>{val}{unit}</td></tr>"

            if fea.get("note"):
                html += (f"<tr><td><b>Note</b></td>"
                         f"<td><i>{fea['note']}</i></td></tr>")
            html += "</table>"

        # Lattice
        lattice = state.get("lattice_evaluation", {})
        if lattice:
            needs = lattice.get("needs_reinforcement", False)
            html += f"<h2>Lattice Reinforcement: <span class='{'warn' if needs else 'pass'}'>"
            html += f"{'NEEDED' if needs else 'Not Required'}</span></h2>"
            if needs:
                spec = lattice.get("lattice_specification", {})
                if spec:
                    html += "<table>"
                    lattice_fields = [
                        ("Type", "type"),
                        ("Relative Density", "relative_density"),
                        ("Strut Diameter", "strut_diameter_mm", " mm"),
                        ("Cell Size", "cell_size_mm", " mm"),
                        ("Material", "material"),
                        ("Location", "location"),
                    ]
                    for item in lattice_fields:
                        label, key = item[0], item[1]
                        unit = item[2] if len(item) > 2 else ""
                        val = spec.get(key)
                        if val is not None:
                            html += f"<tr><td><b>{label}</b></td><td>{val}{unit}</td></tr>"
                    dims = spec.get("dimensions_mm")
                    if dims and len(dims) == 3:
                        html += (f"<tr><td><b>Dimensions</b></td>"
                                 f"<td>{dims[0]} x {dims[1]} x {dims[2]} mm</td></tr>")
                    html += "</table>"

        # Human review
        html += "<h2>Human Review</h2>"
        html += f"<p>Approved: <b>{'Yes' if state.get('human_approved') else 'PENDING'}</b></p>"
        if state.get("human_reviewer"):
            html += f"<p>Reviewer: {state['human_reviewer']}</p>"

        self.report_text.setHtml(html)
