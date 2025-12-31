def neon_stylesheet() -> str:
    return """
    QWidget {
        background-color: #070A12;
        color: #EAF2FF;
        font-size: 14px;
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
    QListWidget::item { padding: 8px; }
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
        min-height: 30px;
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
        background-color: #020403;
        color: #33FF66;
        font-size: 14px;
        font-family: "Courier New", Consolas, monospace;
    }
    QLabel { font-weight: 700; color: #33FF66; }

    QToolBar {
        background: #020403;
        border-bottom: 1px solid rgba(51,255,102,60);
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 6px;
        padding: 6px;
        color: #33FF66;
    }
    QToolButton:hover {
        background: rgba(51,255,102,20);
    }

    QListWidget {
        background: rgba(2,4,3,230);
        border: 1px solid rgba(51,255,102,50);
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(2,4,3,240);
        border: 1px solid rgba(51,255,102,50);
        border-radius: 8px;
        font-family: "Courier New", Consolas, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: rgba(2,4,3,240);
        border: 1px solid rgba(51,255,102,60);
        border-radius: 6px;
        color: #33FF66;
    }

    QStatusBar {
        background: #020403;
        border-top: 1px solid rgba(51,255,102,60);
        color: #33FF66;
    }

    QDialog { background: #020403; }
    """

def clinical_stylesheet() -> str:
    return """
    QWidget {
        background-color: #F7FAFC;
        color: #1F2937;
        font-size: 14px;
        font-family: "Segoe UI", Inter, sans-serif;
    }
    QLabel { font-weight: 600; }

    QToolBar {
        background: #FFFFFF;
        border-bottom: 1px solid #CBD5E1;
        padding: 6px;
    }

    QToolButton {
        background: transparent;
        border-radius: 6px;
        padding: 6px;
    }
    QToolButton:hover {
        background: #E5F0FF;
    }

    QListWidget {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
    }

    QTextEdit {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        font-size: 13px;
    }

    QComboBox, QSpinBox {
        background: #FFFFFF;
        border: 1px solid #94A3B8;
        border-radius: 6px;
        padding: 6px;
    }

    QStatusBar {
        background: #FFFFFF;
        border-top: 1px solid #CBD5E1;
        color: #475569;
    }

    QDialog { background: #FFFFFF; }
    """

def oled_dark_stylesheet() -> str:
    return """
    QWidget {
        background-color: #000000;
        color: #E5E7EB;
        font-size: 14px;
    }
    QLabel { font-weight: 600; }

    QToolBar {
        background: #000000;
        border-bottom: 1px solid #1F2933;
        padding: 6px;
    }

    QToolButton {
        background: transparent;
        border-radius: 8px;
        padding: 6px;
        color: #E5E7EB;
    }
    QToolButton:hover {
        background: rgba(255,255,255,12);
    }

    QListWidget {
        background: #000000;
        border: 1px solid #1F2933;
        border-radius: 10px;
    }

    QTextEdit {
        background: #000000;
        border: 1px solid #1F2933;
        border-radius: 10px;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: #000000;
        border: 1px solid #374151;
        border-radius: 8px;
        color: #E5E7EB;
    }

    QStatusBar {
        background: #000000;
        border-top: 1px solid #1F2933;
        color: #9CA3AF;
    }

    QDialog { background: #000000; }
    """