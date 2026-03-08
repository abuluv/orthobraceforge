"""
OrthoBraceForge — Pipeline Worker Thread
Runs the orchestration pipeline in a background QThread.
"""
from PyQt6.QtCore import QThread, pyqtSignal


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
