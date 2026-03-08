"""
OrthoBraceForge — GUI Themes
Dark and high-contrast Qt stylesheets.
"""

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
