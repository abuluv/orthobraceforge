"""
OrthoBraceForge — Application Entrypoint
Pediatric AFO Design & Manufacturing Suite

Launch sequence:
  1. Configure logging
  2. Show splash screen with regulatory disclaimer
  3. Initialize database + orchestrator
  4. Launch main window
"""
import sys
import os
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen-exe path fixup (PyInstaller)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    os.environ["QT_PLUGIN_PATH"] = str(Path(sys._MEIPASS) / "PyQt6" / "Qt6" / "plugins")


def setup_logging():
    log_dir = Path(os.environ.get("APPDATA", Path.home())) / "OrthoBraceForge" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "orthobraceforge.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    setup_logging()
    logger = logging.getLogger("orthobraceforge")
    logger.info("OrthoBraceForge starting")

    # Import Qt after path fixup
    from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
    from PyQt6.QtGui import QPixmap, QFont, QColor
    from PyQt6.QtCore import Qt, QTimer

    app = QApplication(sys.argv)
    app.setApplicationName("OrthoBraceForge")
    app.setApplicationVersion("1.0.0")

    # --- Splash Screen ---
    splash_pix = QPixmap(600, 340)
    splash_pix.fill(QColor("#1a1a2e"))
    splash = QSplashScreen(splash_pix)
    splash.setStyleSheet(
        "QSplashScreen { border: 2px solid #e94560; }"
    )
    font = QFont("Segoe UI", 11)
    splash.setFont(font)
    splash.showMessage(
        "OrthoBraceForge v1.0.0\n"
        "Pediatric AFO Design & Manufacturing Suite\n\n"
        "⚠ INVESTIGATIONAL USE ONLY — NOT FDA CLEARED\n"
        "All outputs require licensed clinician review.\n\n"
        "Initializing database and agent pipeline…",
        Qt.AlignmentFlag.AlignCenter,
        QColor("#e0e0e0"),
    )
    splash.show()
    app.processEvents()

    # --- Regulatory Acknowledgment (first run) ---
    from config import DB_PATH, REGULATORY_BANNER
    first_run = not DB_PATH.exists()

    # --- Initialize Core Systems ---
    try:
        from database import Database
        from orchestration import OrchoBraceOrchestrator
        from gui import MainWindow

        db = Database()
        orchestrator = OrchoBraceOrchestrator(db=db)
        logger.info("Database and orchestrator initialized")
    except Exception as e:
        logger.exception("Fatal initialization error")
        splash.close()
        QMessageBox.critical(
            None, "Startup Error",
            f"OrthoBraceForge failed to initialize:\n\n{e}\n\n"
            "Check logs in %APPDATA%/OrthoBraceForge/logs/",
        )
        return 1

    # --- Main Window ---
    window = MainWindow(orchestrator)

    splash.finish(window)

    # Show regulatory disclaimer on first run
    if first_run:
        QMessageBox.warning(
            window,
            "⚠ Regulatory Notice",
            REGULATORY_BANNER + "\n\n"
            "By clicking OK you acknowledge that:\n"
            "• This software is for INVESTIGATIONAL USE ONLY\n"
            "• All designs MUST be reviewed by a licensed clinician\n"
            "• No design may be used on a patient without approval\n"
            "• You accept responsibility for clinical decisions",
        )

    window.show()
    logger.info("Main window displayed")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
