def neon_stylesheet() -> str:
    return """
    QWidget {
        background-color: #070A12;
        color: #EAF2FF;
        font-family: "VT323", monospace;
        font-size: 12px;
    }
    QLabel { font-weight: 700; color: #EAF2FF; background: transparent;}

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
        border-radius: 5px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: transparent;
        color: #EAF2FF;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(15, 24, 56, 200);
        border: 1px solid #FFFFFF;
        border-radius: 5px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }
    
    QComboBox {
        background: rgba(15, 24, 56, 200);
        padding: 3px;
        min-height: 15px;
        color: #EAF2FF;
    }
    QSpinBox {
        background: rgba(15, 24, 56, 200);
        padding: 0px;
        min-height: 15px;
        color: #EAF2FF;
    }
    QCheckBox#CBCheckbox {
        background-color: transparent;
        border-radius: 5px;
        padding: 4px;
        border: 1px solid #EAF2FF;
    }

    QStatusBar {
        background: #0B1330;
        border-top: 1px solid rgba(102, 240, 255, 45);
        color: #B7C7E6;
    }

    QDialog { background: #0B1330; }
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 2px;
        border-radius: 50px;
    }

    QScrollBar::handle:vertical {
        background: #EAF2FF;
        min-height: 10px;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """

def retro_terminal_stylesheet() -> str:
    return """
    QWidget {
        background-color: #020402;
        color: #7CFF6B;
        font-size: 10px;
        font-family: "Courier New", Courier, monospace;
    }
    QLabel { font-weight: 700; color: #9CFF8A; background: transparent;}

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
        border-radius: 5px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: transparent;
        color: #9CFF8A;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(6, 12, 6, 240);
        border: 1px solid red;
        border-radius: 5px;
        padding: 8px;
        font-family: "Courier New", Courier, monospace;
        font-size: 12px;
        color: red
    }
    
    QComboBox {
        background: rgba(6, 12, 6, 240);
        padding: 3px;
        min-height: 15px;
        color: #7CFF6B;
    }
    QSpinBox {
        background: rgba(6, 12, 6, 240);
        padding: 0px;
        min-height: 15px;
        color: #7CFF6B;
    }
    QCheckBox#CBCheckbox {
        background-color: transparent;
        border-radius: 5px;
        padding: 4px;
        border: 1px solid #7CFF6B;
    }

    QStatusBar {
        background: #020402;
        border-top: 1px solid rgba(124, 255, 107, 90);
        color: #6BD65E;
    }

    QDialog { background: #020402; }
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 2px;
        border-radius: 50px;
    }

    QScrollBar::handle:vertical {
        background: #7CFF6B;
        min-height: 10px;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """


def clinical_stylesheet() -> str:
    return """
    QWidget {
        background-color: #F6F8FB;
        color: #1E293B;
        font-size: 12px;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #1E293B; background: transparent; }

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
        border-radius: 5px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(59, 130, 246, 25);
        color: #1E293B;
        border-radius: 8px;
    }

    QTextEdit {
        background: #FFFFFF;
        border: 1px solid blue;
        border-radius: 5px;
        padding: 4px;
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 12px;
        color: blue;
    }

    QComboBox {
        background: #FFFFFF;
        padding: 3px;
        min-height: 15px;
        color: #1E293B;
    }
    QSpinBox {
        background: #FFFFFF;
        padding: 0px;
        min-height: 15px;
        color: #1E293B;
    }
    QCheckBox#CBCheckbox {
        background-color: transparent;
        border-radius: 5px;
        padding: 4px;
        border: 1px solid lightgrey;
    }
    
    QStatusBar {
        background: #FFFFFF;
        border-top: 1px solid rgba(30, 41, 59, 40);
        color: #475569;
    }

    QDialog { background: #F6F8FB; }
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 2px;
        border-radius: 50px;
    }

    QScrollBar::handle:vertical {
        background: blue;
        min-height: 10px;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """


def oled_dark_stylesheet() -> str:
    return """
    QWidget {
        background-color: #000000;
        color: #EDEDED;
        font-size: 12px;
        font-family: "Segoe UI", "Inter", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #FFFFFF; background: transparent;}

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
        border-radius: 5px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(255, 255, 255, 22);
        color: #FFFFFF;
        border-radius: 8px;
    }

    QTextEdit {
        background: #000000;
        border: 1px solid cyan;
        border-radius: 5px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
        color: cyan;
    }
    
    QComboBox {
        background: #000000;
        padding: 3px;
        min-height: 15px;
        color: #EDEDED;
    }
    QSpinBox {
        background: #000000;
        padding: 0px;
        min-height: 15px;
        color: #EDEDED;
    }
    QCheckBox#CBCheckbox {
        background-color: transparent;
        border-radius: 5px;
        padding: 4px;
        border: 1px solid cyan;
    }

    QStatusBar {
        background: #000000;
        border-top: 1px solid rgba(255, 255, 255, 35);
        color: #B0B0B0;
    }

    QDialog { background: #000000; }
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 2px;
        border-radius: 50px;
    }

    QScrollBar::handle:vertical {
        background: #EDEDED;
        min-height: 10px;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """

def sunset_synth_stylesheet() -> str:
    return """
    QWidget {
        background-color: #1A1026;
        color: #FFF1F8;
        font-size: 12px;
        font-family: "JetBrains Mono", "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #FFF1F8; background: transparent;}

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
        border-radius: 5px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(255, 209, 102, 35);
        color: #FFF7ED;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(36, 20, 58, 240);
        border: 1px solid orange;
        border-radius: 5px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
        color: orange;
    }

    QComboBox {
        background: rgba(36, 20, 58, 240);
        padding: 3px;
        min-height: 15px;
        color: #FFF1F8
    }
    QSpinBox {
        background: rgba(36, 20, 58, 240);
        padding: 0px;
        min-height: 15px;
        color: #FFF1F8
    }
    QCheckBox#CBCheckbox {
        background-color: transparent;
        border-radius: 5px;
        padding: 4px;
        border: 1px solid orange;
    }

    QStatusBar {
        background: #24143A;
        border-top: 1px solid rgba(185, 131, 255, 80);
        color: #C7BFE6;
    }

    QDialog { background: #1A1026; }
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 2px;
        border-radius: 50px;
    }

    QScrollBar::handle:vertical {
        background: #FFF1F8;
        min-height: 10px;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """


def forest_mist_stylesheet() -> str:
    return """
    QWidget {
        background-color: #0F1C17;
        color: #ECFEF8;
        font-size: 12px;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 600; color: #ECFEF8; background: transparent;}

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
        border-radius: 5px;
    }
    QListWidget::item { padding: 2px; }
    QListWidget::item:selected {
        background: rgba(52, 211, 153, 35);
        color: #ECFEF8;
        border-radius: 8px;
    }

    QTextEdit {
        background: rgba(20, 40, 34, 240);
        border: 1px solid #C4A484;
        border-radius: 5px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
        color: #C4A484;
    }

    QComboBox {
        background: rgba(20, 40, 34, 240);
        padding: 3px;
        min-height: 15px;
        color: #ECFEF8;
    }
    QSpinBox {
        background: rgba(20, 40, 34, 240);
        padding: 0px;
        min-height: 15px;
        color: #ECFEF8;
    }
    QCheckBox#CBCheckbox {
        background-color: transparent;
        border-radius: 5px;
        padding: 4px;
        border: 1px solid #C4A484;
    }

    QStatusBar {
        background: #142822;
        border-top: 1px solid rgba(110, 231, 183, 80);
        color: #9FBFB3;
    }

    QDialog { background: #0F1C17; }
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 2px;
        border-radius: 50px;
    }

    QScrollBar::handle:vertical {
        background: #9FBFB3;
        min-height: 10px;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """

def signal_contrast_stylesheet() -> str:
    return """
    QWidget {
        background-color: #0B0B0B;
        color: #FFFFFF;
        font-size: 12px;
        font-family: "Segoe UI", Arial, sans-serif;
    }
    QLabel { font-weight: 700; color: #FFFFFF; background: transparent;}

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
        border-radius: 5px;
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
        border-radius: 5px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox {
        background: #111111;
        padding: 3px;
        min-height: 15px;
        color: #FFFFFF;
    }
    QSpinBox {
        background: #111111;
        padding: 0px;
        min-height: 15px;
        color: #FFFFFF;
    }
    QCheckBox#CBCheckbox {
        background-color: transparent;
        border-radius: 5px;
        padding: 4px;
        border: 1px solid #FFFFFF;
    }

    QStatusBar {
        background: #111111;
        border-top: 1px solid rgba(255, 255, 255, 55);
        color: #B0BEC5;
    }

    QDialog { background: #0B0B0B; }
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 2px;
        border-radius: 50px;
    }

    QScrollBar::handle:vertical {
        background: #FFFFFF;
        min-height: 10px;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """