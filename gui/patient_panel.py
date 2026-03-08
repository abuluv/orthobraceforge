"""
OrthoBraceForge — Patient Panel Screens
Screen 1: PatientIntakeScreen — demographics, scan upload, clinical notes.
Screen 2: ConditionSelectorScreen — toe walking preset selection.
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import MATERIALS, REGULATORY_BANNER, TOE_WALKING_PRESETS


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
