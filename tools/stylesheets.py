def neon_stylesheet() -> str:
    return """
    QWidget {
        background-color: #070A12;
        color: #EAF2FF;
        font-family: "VT323", monospace;
        font-size: 15px;
    }
    QLabel { font-weight: 700; color: #EAF2FF; }

    QToolBar {
        background: #0B1330;
        border-bottom: 1px solid rgba(102, 240, 255, 60);
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 10px;
        padding: 6px;
        color: #EAF2FF;
    }
    QToolButton:hover {
        background: rgba(102, 240, 255, 18);
    }
    QToolButton:pressed {
        background: rgba(155, 124, 255, 22);
    }

    QListWidget {
        background: rgba(15, 24, 56, 180);
        border: 1px solid rgba(102, 240, 255, 45);
        border-radius: 12px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: transparent;
        color: #EAF2FF;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(15, 24, 56, 200);
        border: 1px solid rgba(102, 240, 255, 45);
        border-radius: 12px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: rgba(15, 24, 56, 200);
        border: 1px solid rgba(155, 124, 255, 55);
        border-radius: 10px;
        padding: 6px;
        min-height: 15px;
        color: #EAF2FF;
    }

    QStatusBar {
        background: #0B1330;
        border-top: 1px solid rgba(102, 240, 255, 45);
        color: #B7C7E6;
    }

    QDialog { background: #0B1330; }
    """

def retro_terminal_stylesheet() -> str:
    return """
    QWidget {
        background-color: #020402;
        color: #7CFF6B;
        font-size: 13px;
        font-family: "Courier New", Courier, monospace;
    }
    QLabel { font-weight: 700; color: #9CFF8A; }

    QToolBar {
        background: #020402;
        border-bottom: 1px solid rgba(124, 255, 107, 120);
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 10px;
        padding: 6px;
        color: #7CFF6B;
    }
    QToolButton:hover {
        background: rgba(124, 255, 107, 30);
    }
    QToolButton:pressed {
        background: rgba(255, 200, 80, 40);
    }

    QListWidget {
        background: rgba(6, 12, 6, 220);
        border: 1px solid rgba(124, 255, 107, 90);
        border-radius: 12px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: transparent;
        color: #9CFF8A;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(6, 12, 6, 240);
        border: 1px solid rgba(124, 255, 107, 90);
        border-radius: 12px;
        padding: 8px;
        font-family: "Courier New", Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: rgba(6, 12, 6, 240);
        border: 1px solid rgba(255, 200, 80, 120);
        border-radius: 10px;
        padding: 6px;
        min-height: 15px;
        color: #7CFF6B;
    }

    QStatusBar {
        background: #020402;
        border-top: 1px solid rgba(124, 255, 107, 90);
        color: #6BD65E;
    }

    QDialog { background: #020402; }
    """


def clinical_stylesheet() -> str:
    return """
    QWidget {
        background-color: #F6F8FB;
        color: #1E293B;
        font-size: 14px;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #1E293B; }

    QToolBar {
        background: #FFFFFF;
        border-bottom: 1px solid rgba(30, 41, 59, 40);
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 10px;
        padding: 6px;
        color: #1E293B;
    }
    QToolButton:hover {
        background: rgba(59, 130, 246, 20);
    }
    QToolButton:pressed {
        background: rgba(59, 130, 246, 35);
    }

    QListWidget {
        background: #FFFFFF;
        border: 1px solid rgba(30, 41, 59, 35);
        border-radius: 12px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(59, 130, 246, 25);
        color: #1E293B;
        border-radius: 8px;
    }

    QTextEdit {
        background: #FFFFFF;
        border: 1px solid rgba(30, 41, 59, 35);
        border-radius: 12px;
        padding: 8px;
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: #FFFFFF;
        border: 1px solid rgba(59, 130, 246, 70);
        border-radius: 10px;
        padding: 6px;
        min-height: 15px;
        color: #1E293B;
    }

    QStatusBar {
        background: #FFFFFF;
        border-top: 1px solid rgba(30, 41, 59, 40);
        color: #475569;
    }

    QDialog { background: #F6F8FB; }
    """


def oled_dark_stylesheet() -> str:
    return """
    QWidget {
        background-color: #000000;
        color: #EDEDED;
        font-size: 14px;
        font-family: "Segoe UI", "Inter", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #FFFFFF; }

    QToolBar {
        background: #000000;
        border-bottom: 1px solid rgba(255, 255, 255, 35);
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 10px;
        padding: 6px;
        color: #EDEDED;
    }
    QToolButton:hover {
        background: rgba(255, 255, 255, 18);
    }
    QToolButton:pressed {
        background: rgba(180, 180, 180, 30);
    }

    QListWidget {
        background: #000000;
        border: 1px solid rgba(255, 255, 255, 35);
        border-radius: 12px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(255, 255, 255, 22);
        color: #FFFFFF;
        border-radius: 8px;
    }

    QTextEdit {
        background: #000000;
        border: 1px solid rgba(255, 255, 255, 35);
        border-radius: 12px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: #000000;
        border: 1px solid rgba(255, 255, 255, 55);
        border-radius: 10px;
        padding: 6px;
        min-height: 15px;
        color: #EDEDED;
    }

    QStatusBar {
        background: #000000;
        border-top: 1px solid rgba(255, 255, 255, 35);
        color: #B0B0B0;
    }

    QDialog { background: #000000; }
    """

def sunset_synth_stylesheet() -> str:
    return """
    QWidget {
        background-color: #1A1026;
        color: #FFF1F8;
        font-size: 14px;
        font-family: "JetBrains Mono", "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #FFF1F8; }

    QToolBar {
        background: #24143A;
        border-bottom: 1px solid rgba(185, 131, 255, 80);
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 10px;
        padding: 6px;
        color: #FFF1F8;
    }
    QToolButton:hover {
        background: rgba(255, 159, 104, 35);
    }
    QToolButton:pressed {
        background: rgba(255, 93, 162, 45);
    }

    QListWidget {
        background: rgba(36, 20, 58, 220);
        border: 1px solid rgba(185, 131, 255, 80);
        border-radius: 12px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(255, 209, 102, 35);
        color: #FFF7ED;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(36, 20, 58, 240);
        border: 1px solid rgba(185, 131, 255, 80);
        border-radius: 12px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: rgba(36, 20, 58, 240);
        border: 1px solid rgba(255, 159, 104, 90);
        border-radius: 10px;
        padding: 6px;
        min-height: 15px;
        color: #FFF1F8;
    }

    QStatusBar {
        background: #24143A;
        border-top: 1px solid rgba(185, 131, 255, 80);
        color: #C7BFE6;
    }

    QDialog { background: #1A1026; }
    """


def forest_mist_stylesheet() -> str:
    return """
    QWidget {
        background-color: #0F1C17;
        color: #ECFEF8;
        font-size: 14px;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #ECFEF8; }

    QToolBar {
        background: #142822;
        border-bottom: 1px solid rgba(110, 231, 183, 80);
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 10px;
        padding: 6px;
        color: #ECFEF8;
    }
    QToolButton:hover {
        background: rgba(110, 231, 183, 30);
    }
    QToolButton:pressed {
        background: rgba(52, 211, 153, 45);
    }

    QListWidget {
        background: rgba(20, 40, 34, 220);
        border: 1px solid rgba(110, 231, 183, 80);
        border-radius: 12px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(52, 211, 153, 35);
        color: #ECFEF8;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(20, 40, 34, 240);
        border: 1px solid rgba(110, 231, 183, 80);
        border-radius: 12px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: rgba(20, 40, 34, 240);
        border: 1px solid rgba(52, 211, 153, 90);
        border-radius: 10px;
        padding: 6px;
        min-height: 15px;
        color: #ECFEF8;
    }

    QStatusBar {
        background: #142822;
        border-top: 1px solid rgba(110, 231, 183, 80);
        color: #9FBFB3;
    }

    QDialog { background: #0F1C17; }
    """

def signal_contrast_stylesheet() -> str:
    return """
    QWidget {
        background-color: #0B0B0B;
        color: #FFFFFF;
        font-size: 15px;
        font-family: "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 700; color: #FFFFFF; }

    QToolBar {
        background: #111111;
        border-bottom: 1px solid rgba(255, 255, 255, 55);
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 10px;
        padding: 6px;
        color: #FFFFFF;
    }
    QToolButton:hover {
        background: rgba(0, 229, 255, 35);
    }
    QToolButton:pressed {
        background: rgba(124, 77, 255, 45);
    }

    QListWidget {
        background: #111111;
        border: 1px solid rgba(255, 255, 255, 55);
        border-radius: 12px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(0, 230, 118, 40);
        color: #FFFFFF;
        border-radius: 8px;
    }

    QTextEdit {
        background: #111111;
        border: 1px solid rgba(255, 255, 255, 55);
        border-radius: 12px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: #111111;
        border: 1px solid rgba(255, 255, 255, 70);
        border-radius: 10px;
        padding: 6px;
        min-height: 15px;
        color: #FFFFFF;
    }

    QStatusBar {
        background: #111111;
        border-top: 1px solid rgba(255, 255, 255, 55);
        color: #B0BEC5;
    }

    QDialog { background: #0B0B0B; }
    """