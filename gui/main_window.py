"""
OrthoBraceForge — Main Application Window
Stacked tab-based navigation across all 6 workflow screens.
"""
import logging

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
)

from config import APP_CLASSIFICATION, APP_NAME, APP_VERSION

from .design_panel import (
    ComplianceReportScreen,
    GenerationProgressScreen,
    Preview3DScreen,
)
from .patient_panel import ConditionSelectorScreen, PatientIntakeScreen
from .print_panel import ExportPrintScreen, HumanReviewDialog
from .theme import DARK_THEME, HIGH_CONTRAST_THEME
from .worker import PipelineWorker

logger = logging.getLogger("orthobraceforge.gui")


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
        import shutil
        state = self._pipeline_state
        if format_type == "stl" and state.get("stl_path"):
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save STL", f"afo_{state.get('design_id', 'export')[:8]}.stl",
                "STL Files (*.stl)")
            if dest:
                shutil.copy2(state["stl_path"], dest)
        elif format_type == "step" and state.get("step_path"):
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save STEP", f"afo_{state.get('design_id', 'export')[:8]}.step",
                "STEP Files (*.step)")
            if dest:
                shutil.copy2(state["step_path"], dest)
        elif format_type == "audit" and state.get("audit_pdf_path"):
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save Audit PDF", f"audit_{state.get('design_id', 'export')[:8]}.pdf",
                "PDF Files (*.pdf)")
            if dest:
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
