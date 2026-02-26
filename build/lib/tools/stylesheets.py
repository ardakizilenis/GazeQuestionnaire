# tools/stylesheets.py

from __future__ import annotations

from dataclasses import dataclass


# Theme definition

@dataclass(frozen=True)
class ThemePalette:
    # Global
    window_bg: str
    text: str
    label_text: str
    font_family: str
    font_size_px: int

    # Toolbar / buttons
    toolbar_bg: str
    toolbar_border_rgba: str
    toolbtn_text: str
    toolbtn_hover_rgba: str
    toolbtn_pressed_rgba: str

    # List
    list_bg: str
    list_border: str | None  # None -> no border
    list_item_selected_bg: str
    list_item_selected_text: str

    # Editors / inputs
    edit_bg: str
    edit_border: str
    edit_text: str

    combo_bg: str
    combo_text: str

    spin_bg: str
    spin_text: str

    # Statusbar
    status_bg: str
    status_border_rgba: str
    status_text: str

    # Dialog
    dialog_bg: str

    # Scrollbar handle
    scrollbar_handle: str

    # Checkbox
    checkbox_border: str
    undo_redo: str

    checkbox_text: str | None = None


# Builder

def build_stylesheet(p: ThemePalette) -> str:
    checkbox_text = p.checkbox_text or p.text

    list_border = ""
    if p.list_border:
        list_border = f"border: {p.list_border};"
    else:
        list_border = "border: none;"

    return f"""
/* --- Global --- */
QWidget {{
    background-color: {p.window_bg};
    color: {p.text};
    font-family: {p.font_family};
    font-size: {p.font_size_px}px;
}}

QLabel {{
    font-weight: 600;
    color: {p.label_text};
    background: transparent;
}}

/* --- Toolbar --- */
QToolBar {{
    background: {p.toolbar_bg};
    border-bottom: 1px solid {p.toolbar_border_rgba};
    spacing: 6px;
    padding: 6px;
}}
QToolBar::separator {{
    background: {p.toolbar_border_rgba};
    width: 1px;
    margin: 6px 8px;
}}
QToolBar QWidget {{
    background: transparent;
}}
QToolButton {{
    background: transparent;
    border-radius: 10px;
    padding: 6px;
    color: {p.toolbtn_text};
}}
QToolButton:hover {{
    background: {p.toolbtn_hover_rgba};
}}
QToolButton:pressed {{
    background: {p.toolbtn_pressed_rgba};
}}

/* --- List --- */
QListWidget {{
    background: {p.list_bg};
    {list_border}
    border-radius: 5px;
}}
QListWidget::item {{
    padding: 2px;
}}
QListWidget::item:selected {{
    background: {p.list_item_selected_bg};
    color: {p.list_item_selected_text};
    border-radius: 8px;
}}

/* --- Text / Editors --- */
QTextEdit {{
    background: {p.edit_bg};
    border: {p.edit_border};
    border-radius: 5px;
    padding: 8px;
    color: {p.edit_text};
    font-family: Consolas, "JetBrains Mono", "Courier New", monospace;
    font-size: 12px;
}}

/* --- Inputs --- */
QComboBox {{
    background: {p.combo_bg};
    padding: 3px;
    min-height: 18px;
    color: {p.combo_text};
    border-radius: 4px;
}}

QSpinBox {{
    background: {p.spin_bg};
    padding: 0px;
    min-height: 18px;
    color: {p.spin_text};
    border-radius: 4px;
}}

QDoubleSpinBox {{
    background: {p.spin_bg};
    padding: 0px;
    min-height: 18px;
    color: {p.spin_text};
    border-radius: 4px;
}}

/* --- Checkbox (targeted via objectName) --- */
QCheckBox#CBCheckbox {{
    background-color: transparent;
    border-radius: 5px;
    padding: 4px;
    border: 1px solid {p.checkbox_border};
    color: {checkbox_text};
}}

/* --- StatusBar --- */
QStatusBar {{
    background: {p.status_bg};
    border-top: 1px solid {p.status_border_rgba};
    color: {p.status_text};
    font-size: 15px;
}}

/* --- Dialog --- */
QDialog {{
    background: {p.dialog_bg};
}}

/* --- Scrollbar --- */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
    border-radius: 50px;
}}
QScrollBar::handle:vertical {{
    background: {p.scrollbar_handle};
    min-height: 10px;
    border-radius: 50px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QToolButton:enabled {{
    background: {p.undo_redo};
}}
QToolButton:disabled {{
    background: {p.undo_redo};
}}

""".strip()


# ----------------------------
# Theme palettes (only colors + typography)
# ----------------------------

_NEON = ThemePalette(
    window_bg="#070A12",
    text="#EAF2FF",
    label_text="#EAF2FF",
    font_family='"VT323", monospace',
    font_size_px=12,

    toolbar_bg="#0B1330",
    toolbar_border_rgba="rgba(102, 240, 255, 60)",
    toolbtn_text="#EAF2FF",
    toolbtn_hover_rgba="rgba(102, 240, 255, 18)",
    toolbtn_pressed_rgba="rgba(155, 124, 255, 22)",

    list_bg="rgba(15, 24, 56, 180)",
    list_border="1px solid rgba(102, 240, 255, 45)",
    list_item_selected_bg="transparent",
    list_item_selected_text="#EAF2FF",

    edit_bg="rgba(15, 24, 56, 200)",
    edit_border="1px solid orange",
    edit_text="orange",

    combo_bg="rgba(15, 24, 56, 200)",
    combo_text="#EAF2FF",

    spin_bg="rgba(15, 24, 56, 200)",
    spin_text="#EAF2FF",

    checkbox_border="#EAF2FF",
    status_bg="#0B1330",
    status_border_rgba="rgba(102, 240, 255, 45)",
    status_text="#B7C7E6",
    dialog_bg="#0B1330",
    scrollbar_handle="#EAF2FF",
    undo_redo="rgba(102, 240, 255, 0.1)"
)

_RETRO = ThemePalette(
    window_bg="#020402",
    text="#7CFF6B",
    label_text="#9CFF8A",
    font_family='"Courier New", Courier, monospace',
    font_size_px=10,

    toolbar_bg="#020402",
    toolbar_border_rgba="rgba(124, 255, 107, 120)",
    toolbtn_text="#7CFF6B",
    toolbtn_hover_rgba="rgba(124, 255, 107, 30)",
    toolbtn_pressed_rgba="rgba(255, 200, 80, 40)",

    list_bg="rgba(6, 12, 6, 220)",
    list_border=None,
    list_item_selected_bg="transparent",
    list_item_selected_text="#9CFF8A",

    edit_bg="rgba(6, 12, 6, 240)",
    edit_border="1px solid #FF3B3B",
    edit_text="#FF3B3B",

    combo_bg="rgba(6, 12, 6, 240)",
    combo_text="#7CFF6B",

    spin_bg="rgba(6, 12, 6, 240)",
    spin_text="#7CFF6B",

    checkbox_border="#7CFF6B",
    status_bg="#020402",
    status_border_rgba="rgba(124, 255, 107, 90)",
    status_text="#6BD65E",
    dialog_bg="#020402",
    scrollbar_handle="#7CFF6B",
    undo_redo="rgba(124, 255, 107, 0.2)"
)

_CLINICAL = ThemePalette(
    window_bg="#F6F8FB",
    text="#1E293B",
    label_text="#1E293B",
    font_family='"Inter", "Segoe UI", Arial, sans-serif',
    font_size_px=12,

    toolbar_bg="#FFFFFF",
    toolbar_border_rgba="rgba(30, 41, 59, 40)",
    toolbtn_text="#1E293B",
    toolbtn_hover_rgba="rgba(59, 130, 246, 20)",
    toolbtn_pressed_rgba="rgba(59, 130, 246, 35)",

    list_bg="#FFFFFF",
    list_border=None,
    list_item_selected_bg="rgba(59, 130, 246, 25)",
    list_item_selected_text="#1E293B",

    edit_bg="#FFFFFF",
    edit_border="1px solid rgba(59, 130, 246, 80)",
    edit_text="#1E293B",

    combo_bg="#FFFFFF",
    combo_text="#1E293B",

    spin_bg="#FFFFFF",
    spin_text="#1E293B",

    checkbox_border="rgba(148, 163, 184, 160)",
    status_bg="#FFFFFF",
    status_border_rgba="rgba(30, 41, 59, 40)",
    status_text="#475569",
    dialog_bg="#F6F8FB",
    scrollbar_handle="rgba(59, 130, 246, 220)",
    undo_redo="rgba(148, 163, 184, 0.1)"
)

_OLED = ThemePalette(
    window_bg="#000000",
    text="#EDEDED",
    label_text="#FFFFFF",
    font_family='"Segoe UI", "Inter", Arial, sans-serif',
    font_size_px=12,

    toolbar_bg="#000000",
    toolbar_border_rgba="rgba(255, 255, 255, 35)",
    toolbtn_text="#EDEDED",
    toolbtn_hover_rgba="rgba(255, 255, 255, 18)",
    toolbtn_pressed_rgba="rgba(180, 180, 180, 30)",

    list_bg="#000000",
    list_border="1px solid rgba(255, 255, 255, 35)",
    list_item_selected_bg="rgba(255, 255, 255, 22)",
    list_item_selected_text="rgba(255, 255, 255, 35)",

    edit_bg="#000000",
    edit_border="1px solid rgba(0, 255, 255, 160)",
    edit_text="#EDEDED",

    combo_bg="#000000",
    combo_text="#EDEDED",

    spin_bg="#000000",
    spin_text="#EDEDED",

    checkbox_border="rgba(0, 255, 255, 160)",
    status_bg="#000000",
    status_border_rgba="rgba(255, 255, 255, 35)",
    status_text="#B0B0B0",
    dialog_bg="#000000",
    scrollbar_handle="#EDEDED",
    undo_redo="rgba(0, 255, 255, 0.2)"
)

_SUNSET = ThemePalette(
    window_bg="#1A1026",
    text="#FFF1F8",
    label_text="#FFF1F8",
    font_family='"JetBrains Mono", "Segoe UI", Arial, sans-serif',
    font_size_px=12,

    toolbar_bg="#24143A",
    toolbar_border_rgba="rgba(185, 131, 255, 80)",
    toolbtn_text="#FFF1F8",
    toolbtn_hover_rgba="rgba(255, 159, 104, 35)",
    toolbtn_pressed_rgba="rgba(255, 93, 162, 45)",

    list_bg="rgba(36, 20, 58, 220)",
    list_border="1px solid rgba(185, 131, 255, 80)",
    list_item_selected_bg="rgba(255, 209, 102, 35)",
    list_item_selected_text="#FFF7ED",

    edit_bg="rgba(36, 20, 58, 240)",
    edit_border="1px solid rgba(255, 165, 0, 180)",
    edit_text="rgba(255, 165, 0, 180)",

    combo_bg="rgba(36, 20, 58, 240)",
    combo_text="#FFF1F8",

    spin_bg="rgba(36, 20, 58, 240)",
    spin_text="#FFF1F8",

    checkbox_border="#FFF1F8",
    status_bg="#24143A",
    status_border_rgba="rgba(185, 131, 255, 80)",
    status_text="#C7BFE6",
    dialog_bg="#1A1026",
    scrollbar_handle="#FFF1F8",
    undo_redo="rgba(255, 165, 0, 0.1)"
)

_FOREST = ThemePalette(
    window_bg="#0F1C17",
    text="#ECFEF8",
    label_text="#ECFEF8",
    font_family='"Inter", "Segoe UI", Arial, sans-serif',
    font_size_px=12,

    toolbar_bg="#142822",
    toolbar_border_rgba="rgba(110, 231, 183, 80)",
    toolbtn_text="#ECFEF8",
    toolbtn_hover_rgba="rgba(110, 231, 183, 30)",
    toolbtn_pressed_rgba="rgba(52, 211, 153, 45)",

    list_bg="rgba(20, 40, 34, 220)",
    list_border="1px solid rgba(110, 231, 183, 80)",
    list_item_selected_bg="rgba(52, 211, 153, 35)",
    list_item_selected_text="#ECFEF8",

    edit_bg="rgba(20, 40, 34, 240)",
    edit_border="1px solid rgba(196, 164, 132, 200)",
    edit_text="rgba(196, 164, 132, 200)",

    combo_bg="rgba(20, 40, 34, 240)",
    combo_text="#ECFEF8",

    spin_bg="rgba(20, 40, 34, 240)",
    spin_text="#ECFEF8",

    checkbox_border="rgba(196, 164, 132, 200)",
    status_bg="#142822",
    status_border_rgba="rgba(110, 231, 183, 80)",
    status_text="#9FBFB3",
    dialog_bg="#0F1C17",
    scrollbar_handle="#9FBFB3",
    undo_redo="rgba(196, 164, 132, 0.1)"
)

_SIGNAL = ThemePalette(
    window_bg="#0B0B0B",
    text="#FFFFFF",
    label_text="#FFFFFF",
    font_family='"Segoe UI", Arial, sans-serif',
    font_size_px=12,

    toolbar_bg="#111111",
    toolbar_border_rgba="rgba(255, 255, 255, 55)",
    toolbtn_text="#FFFFFF",
    toolbtn_hover_rgba="rgba(0, 229, 255, 35)",
    toolbtn_pressed_rgba="rgba(124, 77, 255, 45)",

    list_bg="#111111",
    list_border="1px solid rgba(255, 255, 255, 55)",
    list_item_selected_bg="rgba(0, 230, 118, 40)",
    list_item_selected_text="#FFFFFF",

    edit_bg="#111111",
    edit_border="1px solid rgba(255, 255, 255, 140)",
    edit_text="#FFFFFF",

    combo_bg="#111111",
    combo_text="#FFFFFF",

    spin_bg="#111111",
    spin_text="#FFFFFF",

    checkbox_border="rgba(255, 255, 255, 140)",
    status_bg="#111111",
    status_border_rgba="rgba(255, 255, 255, 55)",
    status_text="#B0BEC5",
    dialog_bg="#0B0B0B",
    scrollbar_handle="#FFFFFF",
    undo_redo="rgba(255, 255, 255, 0.1)"
)


# Public theme functions (same API as before)

def neon_stylesheet() -> str:
    return build_stylesheet(_NEON)

def retro_terminal_stylesheet() -> str:
    return build_stylesheet(_RETRO)

def clinical_stylesheet() -> str:
    return build_stylesheet(_CLINICAL)

def oled_dark_stylesheet() -> str:
    return build_stylesheet(_OLED)

def sunset_synth_stylesheet() -> str:
    return build_stylesheet(_SUNSET)

def forest_mist_stylesheet() -> str:
    return build_stylesheet(_FOREST)

def signal_contrast_stylesheet() -> str:
    return build_stylesheet(_SIGNAL)
