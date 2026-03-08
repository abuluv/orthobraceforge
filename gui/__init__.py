"""
OrthoBraceForge — PyQt6 GUI Package
All screens: Patient Intake, Condition Selector, 3D Preview,
Generation Progress, Compliance Report, Export/Print Queue.

Re-exports all public classes for backward compatibility with
code that previously did `from gui import MainWindow`.
"""
from .design_panel import (
    ComplianceReportScreen,
    GenerationProgressScreen,
    Preview3DScreen,
)
from .main_window import MainWindow
from .patient_panel import ConditionSelectorScreen, PatientIntakeScreen
from .print_panel import ExportPrintScreen, HumanReviewDialog
from .theme import DARK_THEME, HIGH_CONTRAST_THEME
from .worker import PipelineWorker

__all__ = [
    "DARK_THEME",
    "HIGH_CONTRAST_THEME",
    "PipelineWorker",
    "PatientIntakeScreen",
    "ConditionSelectorScreen",
    "Preview3DScreen",
    "GenerationProgressScreen",
    "ComplianceReportScreen",
    "ExportPrintScreen",
    "HumanReviewDialog",
    "MainWindow",
]
