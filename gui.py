"""
OrthoBraceForge — PyQt6 GUI
All screens: Patient Intake, Condition Selector, 3D Preview,
Generation Progress, Compliance Report, Export/Print Queue.

Dark theme, high-contrast accessibility, touch-friendly (48px min targets).
"""
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QFileDialog, QProgressBar,
    QGroupBox, QSplitter, QTabWidget, QMessageBox,
    QDialog, QDialogButtonBox, QScrollArea, QFrame,
    QSizePolicy, QStatusBar, QMenuBar, QToolBar,
    QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QMargins,
)
from PyQt6.QtGui import (
    QFont, QIcon, QAction, QPalette, QColor, QPixmap,
)

from config import (
    APP_NAME, APP_VERSION, APP_CLASSIFICATION, REGULATORY_BANNER,
    TOE_WALKING_PRESETS, MATERIALS, PEDIATRIC_ANTHRO,
    ICONS_DIR, THEMES_DIR,
)

logger = logging.getLogger("orthobraceforge.gui")

# ===========================================================================
# Dark Theme Stylesheet
# ===========================================================================
DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #333366;
    border-radius: 6px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    color: #c0c0ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    background-color: #0f3460;
    color: #ffffff;
    border: 1px solid #1a5276;
    border-radius: 6px;
    padding: 12px 24px;
    min-height: 32px;
    min-width: 80px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1a5276;
    border-color: #5dade2;
}
QPushButton:pressed {
    background-color: #0b2545;
}
QPushButton:disabled {
    background-color: #2c2c3e;
    color: #666;
    border-color: #333;
}
QPushButton#primaryBtn {
    background-color: #e94560;
    border-color: #e94560;
}
QPushButton#primaryBtn:hover {
    background-color: #ff6b81;
}
QPushButton#dangerBtn {
    background-color: #c0392b;
    border-color: #c0392b;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #333366;
    border-radius: 4px;
    padding: 10px;
    min-height: 28px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #5dade2;
}
QTextEdit, QPlainTextEdit {
    background-color: #0f0f23;
    color: #00ff41;
    border: 1px solid #333366;
    border-radius: 4px;
    padding: 8px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11px;
}
QProgressBar {
    border: 1px solid #333366;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    background-color: #16213e;
    min-height: 24px;
}
QProgressBar::chunk {
    background-color: #5dade2;
    border-radius: 3px;
}
QTabWidget::pane {
    border: 1px solid #333366;
    border-radius: 4px;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #16213e;
    color: #a0a0a0;
    padding: 10px 20px;
    border: 1px solid #333366;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 120px;
}
QTabBar::tab:selected {
    background-color: #1a1a2e;
    color: #5dade2;
    border-color: #5dade2;
}
QLabel#banner {
    background-color: #7d0000;
    color: #ffcccc;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 11px;
}
QLabel#sectionTitle {
    color: #5dade2;
    font-size: 16px;
    font-weight: bold;
    padding: 8px 0;
}
QScrollArea {
    border: none;
}
QStatusBar {
    background-color: #0f0f23;
    color: #888;
    border-top: 1px solid #333366;
}
QMenuBar {
    background-color: #0f0f23;
    color: #e0e0e0;
}
QMenuBar::item:selected {
    background-color: #0f3460;
}
"""

HIGH_CONTRAST_THEME = """
QMainWindow, QWidget {
    background-color: #000000;
    color: #ffffff;
    font-size: 15px;
}
QPushButton {
    background-color: #000080;
    color: #ffff00;
    border: 3px solid #ffff00;
    padding: 14px 28px;
    min-height: 40px;
    font-weight: bold;
    font-size: 15px;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    padding: 12px;
    font-size: 15px;
}
QLabel#banner {
    background-color: #ff0000;
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
}
"""


# ===========================================================================
# Worker Thread for Pipeline Execution
# ===========================================================================
class PipelineWorker(QThread):
    """Runs the orchestration pipeline in a background thread."""
    phase_changed = pyqtSignal(str, dict)
    trace_update = pyqtSignal(str)
    human_review_needed = pyqtSignal(dict)
    pipeline_complete = pyqtSignal(dict)
    pipeline_error = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, orchestrator, patient_data, preset_key,
                 scan_path=None, skip_print=True):
        super().__init__()
        self.orchestrator = orchestrator
        self.patient_data = patient_data
        self.preset_key = preset_key
        self.scan_path = scan_path
        self.skip_print = skip_print
        self._state = None

    def run(self):
        try:
            self.orchestrator.set_callbacks(
                on_phase_change=lambda p, s: self.phase_changed.emit(p, s),
                on_trace_update=lambda m: self.trace_update.emit(m),
                on_human_review_needed=lambda s: self.human_review_needed.emit(s),
                on_error=lambda m: self.error_occurred.emit(m),
            )
            self._state = self.orchestrator.run_pipeline(
                self.patient_data, self.preset_key,
                self.scan_path, skip_print=self.skip_print,
            )
            self.pipeline_complete.emit(self._state)
        except Exception as e:
            self.pipeline_error.emit(str(e))


# ===========================================================================
# Screen 1: Patient Intake
# ===========================================================================
class PatientIntakeScreen(QWidget):
    """Patient demographics, scan upload, and clinical notes."""
    submit_clicked = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Regulatory banner
        banner = QLabel(REGULATORY_BANNER)
        banner.setObjectName("banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        title = QLabel("Patient Intake")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Demographics
        demo_group = QGroupBox("Demographics")
        demo_form = QFormLayout()

        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("First name")
        demo_form.addRow("First Name:", self.first_name)

        self.last_name = QLineEdit()
        self.last_name.setPlaceholderText("Last name")
        demo_form.addRow("Last Name:", self.last_name)

        self.dob = QLineEdit()
        self.dob.setPlaceholderText("YYYY-MM-DD")
        demo_form.addRow("Date of Birth:", self.dob)

        self.age = QSpinBox()
        self.age.setRange(2, 18)
        self.age.setValue(6)
        self.age.setSuffix(" years")
        demo_form.addRow("Age:", self.age)

        self.weight = QDoubleSpinBox()
        self.weight.setRange(8.0, 80.0)
        self.weight.setValue(20.0)
        self.weight.setSuffix(" kg")
        demo_form.addRow("Weight:", self.weight)

        self.height = QDoubleSpinBox()
        self.height.setRange(60.0, 180.0)
        self.height.setValue(115.0)
        self.height.setSuffix(" cm")
        demo_form.addRow("Height:", self.height)

        demo_group.setLayout(demo_form)
        form_layout.addRow(demo_group)

        # Clinical
        clinical_group = QGroupBox("Clinical Assessment")
        clinical_form = QFormLayout()

        self.laterality = QComboBox()
        self.laterality.addItems(["bilateral", "left", "right"])
        clinical_form.addRow("Laterality:", self.laterality)

        self.severity = QComboBox()
        self.severity.addItems(["mild", "moderate", "severe"])
        self.severity.setCurrentText("moderate")
        clinical_form.addRow("Severity:", self.severity)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Clinical observations, ROM findings, gait analysis notes…")
        self.notes.setMaximumHeight(100)
        clinical_form.addRow("Notes:", self.notes)

        clinical_group.setLayout(clinical_form)
        form_layout.addRow(clinical_group)

        # Scan Upload
        scan_group = QGroupBox("3D Scan / Measurements")
        scan_form = QFormLayout()

        scan_row = QHBoxLayout()
        self.scan_path = QLineEdit()
        self.scan_path.setPlaceholderText("Path to STL/OBJ/PLY scan file (optional)")
        self.scan_path.setReadOnly(True)
        scan_row.addWidget(self.scan_path)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_scan)
        scan_row.addWidget(browse_btn)
        scan_form.addRow("Scan File:", scan_row)

        video_row = QHBoxLayout()
        self.video_path = QLineEdit()
        self.video_path.setPlaceholderText("Gait video file (optional)")
        self.video_path.setReadOnly(True)
        video_row.addWidget(self.video_path)
        video_btn = QPushButton("Browse…")
        video_btn.clicked.connect(self._browse_video)
        video_row.addWidget(video_btn)
        scan_form.addRow("Gait Video:", video_row)

        scan_group.setLayout(scan_form)
        form_layout.addRow(scan_group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Submit
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.submit_btn = QPushButton("Continue to Condition Selection →")
        self.submit_btn.setObjectName("primaryBtn")
        self.submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(self.submit_btn)
        layout.addLayout(btn_row)

    def _browse_scan(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select 3D Scan File", "",
            "3D Files (*.stl *.obj *.ply *.pts);;All Files (*)",
        )
        if path:
            self.scan_path.setText(path)

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Gait Video", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)",
        )
        if path:
            self.video_path.setText(path)

    def _on_submit(self):
        data = {
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "dob": self.dob.text().strip(),
            "age": self.age.value(),
            "weight_kg": self.weight.value(),
            "height_cm": self.height.value(),
            "laterality": self.laterality.currentText(),
            "severity": self.severity.currentText(),
            "notes": self.notes.toPlainText().strip(),
            "scan_path": self.scan_path.text().strip() or None,
            "video_path": self.video_path.text().strip() or None,
        }
        # Validate required fields
        if not data["first_name"] or not data["last_name"]:
            QMessageBox.warning(self, "Validation", "Patient name is required.")
            return
        if data["age"] < 2:
            QMessageBox.warning(self, "Validation",
                                "Patient must be ≥2 years for AFO intervention.")
            return
        self.submit_clicked.emit(data)


# ===========================================================================
# Screen 2: Condition Selector
# ===========================================================================
class ConditionSelectorScreen(QWidget):
    """Toe walking preset selection with clinical parameter display."""
    preset_selected = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        self._patient_data = {}
        self._setup_ui()

    def set_patient_data(self, data: dict):
        self._patient_data = data

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Condition & AFO Type Selection")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        info = QLabel(
            "Select the clinical classification that best matches the patient's "
            "presentation. Parameters will be pre-loaded from evidence-based presets."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Preset cards
        self.preset_group = QButtonGroup(self)
        cards_layout = QGridLayout()

        for idx, (key, preset) in enumerate(TOE_WALKING_PRESETS.items()):
            card = QGroupBox(preset.name)
            card_layout = QVBoxLayout()

            details = (
                f"AFO Type: {preset.afotype}\n"
                f"Ankle Target: {preset.ankle_dorsiflexion_target_deg}° DF\n"
                f"PF Stop: {preset.plantar_stop_deg}°\n"
                f"Thickness: {preset.thickness_mm}mm\n"
                f"Trim: {preset.trim_line}\n"
                f"Flex Zone: {'Yes' if preset.flex_zone else 'No'}\n"
            )
            detail_label = QLabel(details)
            detail_label.setStyleSheet("font-size: 11px; color: #aaa;")
            card_layout.addWidget(detail_label)

            notes_label = QLabel(preset.notes)
            notes_label.setWordWrap(True)
            notes_label.setStyleSheet("font-size: 10px; color: #888; font-style: italic;")
            card_layout.addWidget(notes_label)

            radio = QRadioButton(f"Select: {preset.name}")
            radio.setProperty("preset_key", key)
            self.preset_group.addButton(radio, idx)
            card_layout.addWidget(radio)

            card.setLayout(card_layout)
            row, col = divmod(idx, 2)
            cards_layout.addWidget(card, row, col)

        layout.addLayout(cards_layout, 1)

        # Material selection
        mat_group = QGroupBox("Material")
        mat_layout = QHBoxLayout()
        self.material_combo = QComboBox()
        for key, mat in MATERIALS.items():
            self.material_combo.addItem(
                f"{mat.name} ({'✓ Biocompat' if mat.iso_10993_biocompat else '✗'})",
                key,
            )
        mat_layout.addWidget(self.material_combo)
        mat_group.setLayout(mat_layout)
        layout.addWidget(mat_group)

        # Buttons
        btn_row = QHBoxLayout()
        back_btn = QPushButton("← Back to Intake")
        back_btn.clicked.connect(lambda: self.preset_selected.emit("__back__", {}))
        btn_row.addWidget(back_btn)
        btn_row.addStretch()

        generate_btn = QPushButton("Generate AFO Design →")
        generate_btn.setObjectName("primaryBtn")
        generate_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(generate_btn)
        layout.addLayout(btn_row)

    def _on_generate(self):
        selected = self.preset_group.checkedButton()
        if not selected:
            QMessageBox.warning(self, "Selection Required",
                                "Please select a toe walking preset.")
            return
        preset_key = selected.property("preset_key")
        material = self.material_combo.currentData()
        self.preset_selected.emit(preset_key, {
            "material": material,
            "patient_data": self._patient_data,
        })


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
            for k, v in fea.items():
                if k != "passed":
                    html += f"<tr><td><b>{k}</b></td><td>{v}</td></tr>"
            html += "</table>"

        # Lattice
        lattice = state.get("lattice_evaluation", {})
        if lattice:
            needs = lattice.get("needs_reinforcement", False)
            html += f"<h2>Lattice Reinforcement: {'NEEDED' if needs else 'Not Required'}</h2>"

        # Human review
        html += "<h2>Human Review</h2>"
        html += f"<p>Approved: <b>{'Yes' if state.get('human_approved') else 'PENDING'}</b></p>"
        if state.get("human_reviewer"):
            html += f"<p>Reviewer: {state['human_reviewer']}</p>"

        self.report_text.setHtml(html)


# ===========================================================================
# Screen 6: Export & Print Queue
# ===========================================================================
class ExportPrintScreen(QWidget):
    """STL/STEP export and MCP print queue management."""
    export_requested = pyqtSignal(str)
    print_requested = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Export & Print")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Export section
        export_group = QGroupBox("Design Export")
        export_layout = QVBoxLayout()

        self.file_list = QPlainTextEdit()
        self.file_list.setReadOnly(True)
        self.file_list.setMaximumHeight(120)
        export_layout.addWidget(self.file_list)

        export_btns = QHBoxLayout()
        self.export_stl_btn = QPushButton("Save STL…")
        self.export_stl_btn.clicked.connect(lambda: self.export_requested.emit("stl"))
        self.export_step_btn = QPushButton("Save STEP…")
        self.export_step_btn.clicked.connect(lambda: self.export_requested.emit("step"))
        self.export_audit_btn = QPushButton("Save Audit PDF…")
        self.export_audit_btn.clicked.connect(lambda: self.export_requested.emit("audit"))
        export_btns.addWidget(self.export_stl_btn)
        export_btns.addWidget(self.export_step_btn)
        export_btns.addWidget(self.export_audit_btn)
        export_layout.addLayout(export_btns)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # Print section
        print_group = QGroupBox("3D Print Queue (MCP)")
        print_layout = QVBoxLayout()

        self.printer_status = QLabel("Printer: Not connected")
        self.printer_status.setStyleSheet("color: #888;")
        print_layout.addWidget(self.printer_status)

        self.print_btn = QPushButton("Send to Printer →")
        self.print_btn.setObjectName("primaryBtn")
        self.print_btn.clicked.connect(self._on_print)
        print_layout.addWidget(self.print_btn)

        self.print_monitor = QPlainTextEdit()
        self.print_monitor.setReadOnly(True)
        self.print_monitor.setPlaceholderText("Print monitoring log…")
        print_layout.addWidget(self.print_monitor, 1)

        print_group.setLayout(print_layout)
        layout.addWidget(print_group, 1)

    def load_state(self, state: dict):
        """Update the export screen with pipeline results."""
        files = state.get("export_paths", [])
        if state.get("stl_path") and state["stl_path"] not in files:
            files.insert(0, state["stl_path"])
        self.file_list.setPlainText("\n".join(files))

        printer = state.get("printer_status", {})
        pstate = printer.get("state", "offline")
        self.printer_status.setText(f"Printer: {pstate}")
        color = "#27ae60" if pstate == "ready" else "#e74c3c"
        self.printer_status.setStyleSheet(f"color: {color};")

    def _on_print(self):
        self.print_requested.emit({})


# ===========================================================================
# Human Review Dialog
# ===========================================================================
class HumanReviewDialog(QDialog):
    """Modal dialog for mandatory human review gate."""

    def __init__(self, state: dict, parent=None):
        super().__init__(parent)
        self.state = state
        self.approved = False
        self.reviewer_name = ""
        self.review_notes = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("⚠ MANDATORY HUMAN REVIEW")
        self.setMinimumSize(700, 500)
        self.setStyleSheet(DARK_THEME)

        layout = QVBoxLayout(self)

        banner = QLabel("MANDATORY CLINICIAN REVIEW REQUIRED")
        banner.setObjectName("banner")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(banner)

        info = QLabel(
            "This design MUST be reviewed and approved by a licensed orthotist "
            "or physician before it can be manufactured or used clinically.\n\n"
            "Review the design parameters, FEA results, and compliance report "
            "before making your determination."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Design summary
        summary_group = QGroupBox("Design Summary")
        summary_layout = QFormLayout()
        summary_layout.addRow("Patient:",
            QLabel(f"{self.state.get('patient', {}).get('first_name', 'N/A')} "
                   f"{self.state.get('patient', {}).get('last_name', '')}"))
        summary_layout.addRow("Severity:", QLabel(self.state.get("severity", "N/A")))
        summary_layout.addRow("CAD Engine:", QLabel(self.state.get("cad_engine", "N/A")))

        fea = self.state.get("fea_result", {})
        fea_text = f"SF={fea.get('safety_factor', 'N/A')}"
        if fea.get("passed"):
            summary_layout.addRow("FEA:", QLabel(f"✓ PASSED ({fea_text})"))
        else:
            summary_layout.addRow("FEA:", QLabel(f"✗ FAILED ({fea_text})"))

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Reviewer input
        review_group = QGroupBox("Reviewer Information")
        review_form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Licensed Orthotist / Physician name and credentials")
        review_form.addRow("Reviewer:", self.name_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Review notes, modifications needed, or approval rationale…")
        self.notes_input.setMaximumHeight(100)
        review_form.addRow("Notes:", self.notes_input)

        review_group.setLayout(review_form)
        layout.addWidget(review_group)

        # Buttons
        btn_layout = QHBoxLayout()

        reject_btn = QPushButton("✗ REJECT Design")
        reject_btn.setObjectName("dangerBtn")
        reject_btn.clicked.connect(self._reject)
        btn_layout.addWidget(reject_btn)

        btn_layout.addStretch()

        approve_btn = QPushButton("✓ APPROVE for Manufacturing")
        approve_btn.setObjectName("primaryBtn")
        approve_btn.clicked.connect(self._approve)
        btn_layout.addWidget(approve_btn)

        layout.addLayout(btn_layout)

    def _approve(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Required",
                                "Reviewer name and credentials are required for approval.")
            return
        self.approved = True
        self.reviewer_name = self.name_input.text().strip()
        self.review_notes = self.notes_input.toPlainText().strip()
        self.accept()

    def _reject(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Required",
                                "Reviewer name is required for rejection.")
            return
        if not self.notes_input.toPlainText().strip():
            QMessageBox.warning(self, "Required",
                                "Rejection reason is required.")
            return
        self.approved = False
        self.reviewer_name = self.name_input.text().strip()
        self.review_notes = self.notes_input.toPlainText().strip()
        self.accept()


# ===========================================================================
# Main Window
# ===========================================================================
class MainWindow(QMainWindow):
    """Main application window with stacked screen navigation."""

    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self._pipeline_state = {}
        self._pipeline_worker = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(DARK_THEME)

        # Central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create all screens
        self.intake_screen = PatientIntakeScreen()
        self.condition_screen = ConditionSelectorScreen()
        self.progress_screen = GenerationProgressScreen()
        self.preview_screen = Preview3DScreen()
        self.compliance_screen = ComplianceReportScreen()
        self.export_screen = ExportPrintScreen()

        # Add tabs
        self.tabs.addTab(self.intake_screen, "1. Patient Intake")
        self.tabs.addTab(self.condition_screen, "2. Condition")
        self.tabs.addTab(self.progress_screen, "3. Generation")
        self.tabs.addTab(self.preview_screen, "4. 3D Preview")
        self.tabs.addTab(self.compliance_screen, "5. Compliance")
        self.tabs.addTab(self.export_screen, "6. Export / Print")

        # Disable tabs 2-6 initially
        for i in range(1, 6):
            self.tabs.setTabEnabled(i, False)

        # Connect signals
        self.intake_screen.submit_clicked.connect(self._on_intake_complete)
        self.condition_screen.preset_selected.connect(self._on_preset_selected)
        self.export_screen.export_requested.connect(self._on_export)

        # Status bar
        self.statusBar().showMessage(f"{APP_NAME} v{APP_VERSION} | {APP_CLASSIFICATION}")

        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Patient", self)
        new_action.triggered.connect(self._reset)
        file_menu.addAction(new_action)

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("&View")
        hc_action = QAction("&High Contrast Mode", self)
        hc_action.setCheckable(True)
        hc_action.triggered.connect(self._toggle_high_contrast)
        view_menu.addAction(hc_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _on_intake_complete(self, patient_data: dict):
        """Patient intake submitted — move to condition selection."""
        self.condition_screen.set_patient_data(patient_data)
        self._patient_data = patient_data
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

    def _on_preset_selected(self, preset_key: str, extra: dict):
        """Condition preset selected — start pipeline."""
        if preset_key == "__back__":
            self.tabs.setCurrentIndex(0)
            return

        # Enable generation tab and switch
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)

        # Start pipeline in background thread
        self._pipeline_worker = PipelineWorker(
            self.orchestrator,
            self._patient_data,
            preset_key,
            scan_path=self._patient_data.get("scan_path"),
        )
        self._pipeline_worker.phase_changed.connect(self._on_phase_changed)
        self._pipeline_worker.trace_update.connect(self._on_trace)
        self._pipeline_worker.human_review_needed.connect(self._on_human_review)
        self._pipeline_worker.pipeline_complete.connect(self._on_pipeline_complete)
        self._pipeline_worker.pipeline_error.connect(self._on_pipeline_error)
        self._pipeline_worker.error_occurred.connect(self._on_agent_error)
        self._pipeline_worker.start()

    def _on_phase_changed(self, phase: str, state: dict):
        self._pipeline_state = state
        self.progress_screen.update_phase(phase, state)
        self.statusBar().showMessage(f"Phase: {phase}")

    def _on_trace(self, message: str):
        self.progress_screen.append_trace(message)

    def _on_human_review(self, state: dict):
        """Show the mandatory human review dialog."""
        dialog = HumanReviewDialog(state, parent=self)
        dialog.exec()

        if dialog.approved:
            self.orchestrator.approve_design(
                state, dialog.reviewer_name, dialog.review_notes
            )
            state["human_approved"] = True
        else:
            self.orchestrator.reject_design(
                state, dialog.reviewer_name, dialog.review_notes
            )
            state["human_approved"] = False
        self._pipeline_state = state

    def _on_pipeline_complete(self, state: dict):
        """Pipeline finished — enable all tabs and load results."""
        self._pipeline_state = state

        # Enable remaining tabs
        for i in range(3, 6):
            self.tabs.setTabEnabled(i, True)

        # Load 3D preview
        if state.get("stl_path"):
            self.preview_screen.load_mesh(state["stl_path"])

        # Load compliance report
        self.compliance_screen.load_report(state)

        # Load export screen
        self.export_screen.load_state(state)

        # Show warnings
        warnings = state.get("warnings", [])
        if warnings:
            self.progress_screen.show_warnings(warnings)

        # Switch to preview
        self.tabs.setCurrentIndex(3)
        self.statusBar().showMessage("Pipeline complete — review design")

    def _on_pipeline_error(self, error: str):
        QMessageBox.critical(self, "Pipeline Error", f"An error occurred:\n\n{error}")
        self.statusBar().showMessage(f"Error: {error}")

    def _on_agent_error(self, error: str):
        self.statusBar().setStyleSheet("QStatusBar { color: #e94560; }")
        self.statusBar().showMessage(f"Warning: {error}")

    def _on_export(self, format_type: str):
        """Handle export button clicks."""
        state = self._pipeline_state
        if format_type == "stl" and state.get("stl_path"):
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save STL", f"afo_{state.get('design_id', 'export')[:8]}.stl",
                "STL Files (*.stl)")
            if dest:
                import shutil
                shutil.copy2(state["stl_path"], dest)
        elif format_type == "step" and state.get("step_path"):
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save STEP", f"afo_{state.get('design_id', 'export')[:8]}.step",
                "STEP Files (*.step)")
            if dest:
                import shutil
                shutil.copy2(state["step_path"], dest)
        elif format_type == "audit" and state.get("audit_pdf_path"):
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save Audit PDF", f"audit_{state.get('design_id', 'export')[:8]}.pdf",
                "PDF Files (*.pdf)")
            if dest:
                import shutil
                shutil.copy2(state["audit_pdf_path"], dest)

    def _toggle_high_contrast(self, checked: bool):
        if checked:
            self.setStyleSheet(HIGH_CONTRAST_THEME)
        else:
            self.setStyleSheet(DARK_THEME)

    def _show_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>Pediatric AFO Design & Manufacturing Suite</p>"
            f"<p><b>{APP_CLASSIFICATION}</b></p>"
            f"<p>This software generates custom ankle-foot orthoses for "
            f"correction of pediatric idiopathic toe walking (equinus gait).</p>"
            f"<p>All designs require review by a licensed orthotist or physician.</p>",
        )

    def _reset(self):
        """Reset for a new patient."""
        for i in range(1, 6):
            self.tabs.setTabEnabled(i, False)
        self.tabs.setCurrentIndex(0)
        self._pipeline_state = {}
