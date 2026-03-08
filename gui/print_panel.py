"""
OrthoBraceForge — Print Panel
Screen 6: ExportPrintScreen — STL/STEP export and MCP print queue.
HumanReviewDialog — mandatory clinician review gate.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .theme import DARK_THEME


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
