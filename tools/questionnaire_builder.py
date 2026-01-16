#!/usr/bin/env python3
import json
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal, QEvent
from PySide6.QtGui import QAction, QFont, QColor, QPainter, QUndoCommand, QUndoStack, QFontMetrics
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QComboBox, QSpinBox,
    QFileDialog, QMessageBox, QFormLayout, QDialog, QDialogButtonBox,
    QLabel, QToolBar, QStyle, QStyledItemDelegate, QCheckBox, QGroupBox, QLineEdit
)

from tools.themes import TYPE_COLOR_THEMES
from tools.stylesheets import *

# ---- Theme registry (single source of truth) ----
THEME_REGISTRY = {
    "neon": {"label": "Neon", "stylesheet": neon_stylesheet, "app_font": ("Segoe UI", 11)},
    "retro_terminal": {"label": "Retro Terminal", "stylesheet": retro_terminal_stylesheet, "app_font": ("Segoe UI", 11)},
    "clinical": {"label": "Clinical", "stylesheet": clinical_stylesheet, "app_font": ("Segoe UI", 11)},
    "oled_dark": {"label": "Oled Dark", "stylesheet": oled_dark_stylesheet, "app_font": ("Segoe UI", 11)},
    "sunset_synth": {"label": "Sunset Synth", "stylesheet": sunset_synth_stylesheet, "app_font": ("Segoe UI", 11)},
    "forest_mist": {"label": "Forest Mist", "stylesheet": forest_mist_stylesheet, "app_font": ("Segoe UI", 11)},
    "signal_contrast": {"label": "Signal Contrast", "stylesheet": signal_contrast_stylesheet, "app_font": ("Segoe UI", 11)},
}

QUESTION_TYPES = ["info", "yesno", "mcq", "likert", "textgrid", "sp_yesno", "sp_mcq", "sp_likert"]
ACTIVATIONS = ["dwell", "blink"]

CALIBRATIONS = ["9-point", "5-point", "lissajous"]
DEFAULT_CALIBRATION = "9-point"

FILTERS = ["kalman", "kde", "no-filter"]
DEFAULT_FILTER = "kalman"

DEFAULT_DWELL_TIME = 1000   # ms
DEFAULT_BLINK_TIME = 400    # ms

BUILDER_THEMES = list(THEME_REGISTRY.keys())
THEME_NAMES = [THEME_REGISTRY[k]["label"] for k in BUILDER_THEMES]
DEFAULT_THEME = "clinical"

# ------------------ helpers ------------------

def pretty_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)

def type_colors(theme: str) -> dict:
    fallback_theme = "clinical"
    theme_map = TYPE_COLOR_THEMES.get(theme, TYPE_COLOR_THEMES[fallback_theme])
    base = TYPE_COLOR_THEMES[fallback_theme]
    merged = dict(base)
    merged.update(theme_map)
    return merged

def apply_theme(app: QApplication, theme_key: str):
    app.setStyle("Fusion")
    cfg = THEME_REGISTRY.get(theme_key, THEME_REGISTRY[DEFAULT_THEME])
    family, size = cfg.get("app_font", ("Segoe UI", 11))
    app.setFont(QFont(family, size))
    app.setStyleSheet(cfg["stylesheet"]())

def normalize_theme(theme_key: str) -> str:
    return theme_key if theme_key in THEME_REGISTRY else DEFAULT_THEME

def set_combo_by_data(combo: QComboBox, value):
    combo.blockSignals(True)
    i = combo.findData(value)
    if i >= 0:
        combo.setCurrentIndex(i)
    combo.blockSignals(False)

def set_checkbox_silent(cb: QCheckBox, checked: bool):
    cb.blockSignals(True)
    cb.setChecked(bool(checked))
    cb.blockSignals(False)

def set_spin_silent(spin: QSpinBox, value: int):
    spin.blockSignals(True)
    spin.setValue(int(value))
    spin.blockSignals(False)

def make_labeled_row(label_text: str, widget: QWidget) -> QWidget:
    row = QWidget()
    row_l = QHBoxLayout(row)
    row_l.setContentsMargins(0, 0, 0, 0)
    row_l.setSpacing(6)
    row_l.addWidget(QLabel(label_text))
    row_l.addWidget(widget)
    return row

def make_vblock(rows: list[QWidget]) -> QWidget:
    w = QWidget()
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(2)
    for r in rows:
        l.addWidget(r)
    return w

def qtype_to_label(qtype: str) -> str:
    if qtype in ["likert", "sp_likert"]:
        return "Likert Scale"
    if qtype in ["yesno", "sp_yesno"]:
        return "Yes/No"
    if qtype in ["mcq", "sp_mcq"]:
        return "MC-Question"
    if qtype == "textgrid":
        return "Text"
    return qtype.capitalize()

def activation_to_label(act: str) -> str:
    act = (act or "").strip().lower()
    if act == "smooth_pursuit":
        return "Smooth Pursuit"
    if not act:
        return ""
    return act.replace("_", " ").title()


# ------------------ DnD list widget ------------------

class ReorderListWidget(QListWidget):
    orderChanged = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setSelectionMode(QListWidget.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QListWidget.InternalMove)

        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.viewport().setCursor(Qt.ArrowCursor)

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            et = event.type()
            if et in (QEvent.MouseMove, QEvent.Enter):
                over_item = self.itemAt(event.pos()) is not None
                self.viewport().setCursor(Qt.OpenHandCursor if over_item else Qt.ArrowCursor)
        return super().eventFilter(obj, event)

    def startDrag(self, supportedActions):
        self.viewport().setCursor(Qt.ClosedHandCursor)
        try:
            super().startDrag(supportedActions)
        finally:
            pos = self.viewport().mapFromGlobal(self.cursor().pos())
            over_item = self.itemAt(pos) is not None
            self.viewport().setCursor(Qt.OpenHandCursor if over_item else Qt.ArrowCursor)

    def dropEvent(self, event):
        selected_obj = None
        cur = self.currentItem()
        if cur is not None:
            selected_obj = cur.data(Qt.UserRole)

        super().dropEvent(event)

        if selected_obj is not None:
            for i in range(self.count()):
                it = self.item(i)
                if it is not None and it.data(Qt.UserRole) is selected_obj:
                    self.setCurrentRow(i)
                    it.setSelected(True)
                    break

        self.orderChanged.emit()

# ------------------ Item Editor ------------------

class CardItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, get_theme=lambda: "clinical"):
        super().__init__(parent)
        self.get_theme = get_theme

    def paint(self, painter: QPainter, option, index):
        painter.save()

        theme = self.get_theme()
        palette = type_colors(theme)

        it = index.data(Qt.UserRole) or {}
        qtype = it.get("type", "info")
        q_label = qtype_to_label(qtype)

        a_label = activation_to_label(it.get("activation", ""))

        c = palette.get(qtype, palette["info"])
        r = option.rect.adjusted(10, 6, -10, -6)
        bg = QColor(c["bg"])
        fg = QColor(c["fg"])

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(bg)
        painter.drawRoundedRect(r, 10, 10)

        fm = QFontMetrics(painter.font())
        pad_x, pad_y = 8, 4
        gap = 6
        top = r.top() + 10
        right = r.right() - 10

        is_selected = bool(option.state & QStyle.State_Selected)
        if is_selected:
            border = QColor(fg)
            border.setAlpha(220)
            pen = painter.pen()
            pen.setColor(border)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 10, 10)
            painter.setPen(Qt.NoPen)

            hl = QColor(fg)
            hl.setAlpha(25)
            painter.setBrush(hl)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(r, 10, 10)

        def badge_rect_for_text(text: str, right_edge: int):
            tw = fm.horizontalAdvance(text)
            th = fm.height()
            rect = r.adjusted(0, 0, 0, 0)
            rect.setTop(top)
            rect.setBottom(top + th + 2 * pad_y)
            rect.setRight(right_edge)
            rect.setLeft(right_edge - (tw + 2 * pad_x))
            return rect

        duration_text = None
        if q_label == "Info":
            duration_text = f"{int(it.get('duration', 5) or 5)}s"

        secondary_text = duration_text if duration_text is not None else (a_label if a_label else None)

        secondary_rect = None
        if secondary_text:
            secondary_rect = badge_rect_for_text(secondary_text, right)
            secondary_bg = QColor(fg)
            secondary_bg.setAlpha(40)
            painter.setBrush(secondary_bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(secondary_rect, 8, 8)

            painter.setPen(fg)
            painter.drawText(
                secondary_rect.adjusted(pad_x, pad_y, -pad_x, -pad_y),
                Qt.AlignVCenter | Qt.AlignRight,
                secondary_text
            )

        qtype_text = str(q_label)
        qtype_right_edge = (secondary_rect.left() - gap) if secondary_rect else right
        qtype_rect = badge_rect_for_text(qtype_text, qtype_right_edge)

        qtype_bg = QColor(fg)
        qtype_bg.setAlpha(70)
        painter.setBrush(qtype_bg)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(qtype_rect, 8, 8)

        painter.setPen(fg)
        painter.drawText(
            qtype_rect.adjusted(pad_x, pad_y, -pad_x, -pad_y),
            Qt.AlignVCenter | Qt.AlignRight,
            qtype_text
        )

        text = index.data(Qt.DisplayRole) or ""
        text_rect = r.adjusted(14, 10, -14, -10)
        painter.setPen(fg)
        painter.drawText(text_rect, Qt.TextWordWrap | Qt.AlignVCenter, text)

        painter.restore()

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(56, base.height() + 18))


class ItemEditorDialog(QDialog):
    def __init__(self, parent=None, existing=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Item")
        self.resize(560, 480)

        self.type_box = QComboBox()
        self.type_box.addItems(QUESTION_TYPES)

        self.activation_box = QComboBox()
        self.activation_box.addItems(ACTIVATIONS)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Question / info text...")

        self.duration_label = QLabel("Duration:")
        self.activation_label = QLabel("Activation:")

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 999)
        self.duration_spin.setValue(5)

        # ---- Labels as individual inputs (max 5) ----
        self.labels_group = QGroupBox()
        self.labels_group.setTitle("Labels")
        self.labels_group.setVisible(False)

        labels_layout = QVBoxLayout(self.labels_group)
        labels_layout.setContentsMargins(10, 10, 10, 10)
        labels_layout.setSpacing(8)

        self.label_edits: list[QLineEdit] = []
        for i in range(5):
            le = QLineEdit()
            le.setPlaceholderText(f"Label {i + 1}")
            self.label_edits.append(le)
            labels_layout.addWidget(le)

        self.activation_row = QWidget()
        act_layout = QHBoxLayout(self.activation_row)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.addWidget(self.activation_box)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.addRow("Type", self.type_box)
        form.addRow(self.activation_label, self.activation_row)
        form.addRow("Text", self.text_edit)
        form.addRow(self.duration_label, self.duration_spin)
        form.addRow(self.labels_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.type_box.currentTextChanged.connect(self._update_visibility)
        self._update_visibility(self.type_box.currentText())

        if existing:
            self._load(existing)

    def _update_visibility(self, qtype: str):
        is_info = (qtype == "info")
        self.duration_spin.setEnabled(is_info)
        self.duration_spin.setVisible(is_info)
        self.duration_label.setVisible(is_info)

        is_not_sp = qtype not in ("sp_likert", "sp_mcq", "sp_yesno", "info")
        self.activation_box.setEnabled(is_not_sp)
        self.activation_box.setVisible(is_not_sp)
        self.activation_label.setVisible(is_not_sp)

        needs_labels = qtype in ("mcq", "likert", "sp_mcq", "sp_likert")
        self.labels_group.setVisible(needs_labels)
        if not needs_labels:
            return

        n = 4 if qtype in ("mcq", "sp_mcq") else 5
        for i, le in enumerate(self.label_edits):
            le.setVisible(i < n)

    def _load(self, it: dict):
        self.type_box.setCurrentText(it.get("type", "info"))
        self.text_edit.setPlainText(it.get("text", ""))
        if it.get("activation") in ACTIVATIONS:
            self.activation_box.setCurrentText(it["activation"])
        self.duration_spin.setValue(int(it.get("duration", 5) or 5))

        labels = it.get("labels", [])
        for le in self.label_edits:
            le.setText("")
        if isinstance(labels, list):
            for i, val in enumerate(labels[:5]):
                self.label_edits[i].setText(str(val))

    def _collect_labels(self) -> list[str]:
        qtype = self.type_box.currentText()
        n = 4 if qtype in ("mcq", "sp_mcq") else 5 if qtype in ("likert", "sp_likert") else 0
        out = []
        for i in range(n):
            t = self.label_edits[i].text().strip()
            if t:
                out.append(t)
        return out

    def get_item(self) -> dict:
        qtype = self.type_box.currentText()
        it = {"type": qtype, "text": self.text_edit.toPlainText().strip()}

        if qtype == "info":
            it["duration"] = int(self.duration_spin.value())
            return it

        if qtype == "sp_yesno":
            it["activation"] = "smooth_pursuit"
            return it

        if qtype in ("sp_mcq", "sp_likert"):
            it["activation"] = "smooth_pursuit"
            it["labels"] = self._collect_labels()
            return it

        it["activation"] = self.activation_box.currentText()
        if qtype in ("mcq", "likert"):
            it["labels"] = self._collect_labels()
        return it

    def accept(self):
        it = self.get_item()

        if not it.get("text"):
            QMessageBox.warning(self, "Invalid", "Text must not be empty.")
            return

        if it["type"] in ("mcq", "sp_mcq") and len(it.get("labels", [])) != 4:
            QMessageBox.warning(self, "Invalid", "MCQ requires exactly 4 labels.")
            return

        if it["type"] in ("likert", "sp_likert") and len(it.get("labels", [])) != 5:
            QMessageBox.warning(self, "Invalid", "Likert requires exactly 5 labels.")
            return

        super().accept()

# ------------------ Undo / Redo ------------------

class AddItemCommand(QUndoCommand):
    def __init__(self, win, item: dict, index: int | None = None):
        super().__init__()
        self.win = win
        self.item = item
        self.index = index

    def redo(self):
        if self.index is None or self.index > len(self.win.items):
            self.win.items.append(self.item)
            self.index = len(self.win.items) - 1
        else:
            self.win.items.insert(self.index, self.item)
        self.win.refresh()
        self.win.list_widget.setCurrentRow(self.index)

    def undo(self):
        if 0 <= self.index < len(self.win.items):
            del self.win.items[self.index]
        self.win.refresh()


class DeleteItemCommand(QUndoCommand):
    def __init__(self, win, index: int, item: dict):
        super().__init__()
        self.win = win
        self.index = index
        self.item = item

    def redo(self):
        if 0 <= self.index < len(self.win.items):
            del self.win.items[self.index]
        self.win.refresh()
        self.win.list_widget.setCurrentRow(min(self.index, len(self.win.items) - 1))

    def undo(self):
        if self.index > len(self.win.items):
            self.index = len(self.win.items)
        self.win.items.insert(self.index, self.item)
        self.win.refresh()
        self.win.list_widget.setCurrentRow(self.index)


class EditItemCommand(QUndoCommand):
    def __init__(self, win, index: int, old_item: dict, new_item: dict):
        super().__init__()
        self.win = win
        self.index = index
        self.old_item = old_item
        self.new_item = new_item

    def redo(self):
        if 0 <= self.index < len(self.win.items):
            self.win.items[self.index] = self.new_item
        self.win.refresh()
        self.win.list_widget.setCurrentRow(self.index)

    def undo(self):
        if 0 <= self.index < len(self.win.items):
            self.win.items[self.index] = self.old_item
        self.win.refresh()
        self.win.list_widget.setCurrentRow(self.index)


class ReorderItemsCommand(QUndoCommand):
    def __init__(self, win, old_order: list[dict], new_order: list[dict]):
        super().__init__()
        self.win = win
        self.old_order = old_order
        self.new_order = new_order

    def redo(self):
        self.win.items = list(self.new_order)
        self.win.refresh()

    def undo(self):
        self.win.items = list(self.old_order)
        self.win.refresh()

# ------------------ Main Window ------------------

class BuilderMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.filename = "*"
        self.version = 1.3
        self.resize(1150, 700)
        self.update_window_title()

        self.items: list[dict] = []
        self.current_path: Path | None = None
        self.gazepoint_blocked: bool = False

        self.calibration: str = DEFAULT_CALIBRATION
        self.filter: str = DEFAULT_FILTER
        self.theme = DEFAULT_THEME

        apply_theme(QApplication.instance(), self.theme)

        self.undo_stack = QUndoStack(self)

        self._build_toolbar()
        self._build_ui()

        self.statusBar().showMessage("Ready")

    def update_window_title(self):
        shown = self.filename if self.filename else "*"
        self.setWindowTitle(f"Questionnaire Builder ({shown})")

    # ---------- UI ----------

    def _make_action(self, icon_enum, text: str, tooltip: str, shortcut: str | None = None) -> QAction:
        st = self.style()
        act = QAction(st.standardIcon(icon_enum), text, self)
        act.setToolTip(tooltip)
        if shortcut:
            act.setShortcut(shortcut)
        return act

    def _add_actions(self, actions: list[QAction]):
        for a in actions:
            self.tb.addAction(a)
            w = self.tb.widgetForAction(a)
            if w:
                w.setCursor(Qt.PointingHandCursor)

    def _build_toolbar(self):
        self.tb = QToolBar("Main")
        self.tb.setIconSize(QSize(17, 17))
        self.tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(self.tb)

        # -------- Actions --------
        self.act_add = self._make_action(QStyle.SP_FileDialogNewFolder, "Add", "Add New Question (Ctrl+A)", "Ctrl+A")
        self.act_new = self._make_action(QStyle.SP_FileIcon, "New", "New File / Reset (Ctrl+N)", "Ctrl+N")
        self.act_open = self._make_action(QStyle.SP_DialogOpenButton, "Open", "Open JSON-File (Ctrl+O)", "Ctrl+O")
        self.act_save = self._make_action(QStyle.SP_DialogSaveButton, "Save", "Save JSON-File (Ctrl+S)", "Ctrl+S")
        self.act_edit = self._make_action(QStyle.SP_DesktopIcon, "Edit", "Edit Question (Ctrl+E)", "Ctrl+E")
        self.act_del = self._make_action(QStyle.SP_TrashIcon, "Delete", "Delete Question (Backspace)", "Backspace")

        self.act_undo = self.undo_stack.createUndoAction(self, "Undo")
        self.act_undo.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.act_undo.setShortcut("Ctrl+Z")

        self.act_redo = self.undo_stack.createRedoAction(self, "Redo")
        self.act_redo.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.act_redo.setShortcut("Ctrl+Y")

        # -------- Calibration Box --------
        self.calibration_box = QComboBox()
        self.calibration_box.setFixedWidth(90)
        for key_calibration in CALIBRATIONS:
            self.calibration_box.addItem(key_calibration, key_calibration)
        self.calibration_box.currentIndexChanged.connect(self.on_calibration_changed)
        self.calibration_box.setCursor(Qt.PointingHandCursor)

        # -------- Filter Box --------
        self.filter_box = QComboBox()
        self.filter_box.setFixedWidth(90)
        for key_filter in FILTERS:
            self.filter_box.addItem(key_filter, key_filter)
        self.filter_box.currentIndexChanged.connect(self.on_filter_changed)
        self.filter_box.setCursor(Qt.PointingHandCursor)

        # -------- Dwell/Blink Spins --------
        self.dwell_time: int = DEFAULT_DWELL_TIME
        self.dwell_spin = QSpinBox()
        self.dwell_spin.setFixedWidth(90)
        self.dwell_spin.setRange(750, 6000)
        self.dwell_spin.setSingleStep(50)
        self.dwell_spin.setSuffix(" ms")
        self.dwell_spin.setValue(self.dwell_time)
        self.dwell_spin.valueChanged.connect(self.on_dwell_changed)
        self.dwell_spin.setCursor(Qt.PointingHandCursor)

        self.blink_time: int = DEFAULT_BLINK_TIME
        self.blink_spin = QSpinBox()
        self.blink_spin.setFixedWidth(90)
        self.blink_spin.setRange(50, 2000)
        self.blink_spin.setSingleStep(50)
        self.blink_spin.setSuffix(" ms")
        self.blink_spin.setValue(self.blink_time)
        self.blink_spin.valueChanged.connect(self.on_blink_changed)
        self.blink_spin.setCursor(Qt.PointingHandCursor)

        # -------- Theme Box --------
        self.theme_box = QComboBox()
        for key_theme in BUILDER_THEMES:
            label = THEME_NAMES[BUILDER_THEMES.index(key_theme)]
            self.theme_box.addItem(label, key_theme)
        i = self.theme_box.findData(self.theme)
        if i >= 0:
            self.theme_box.setCurrentIndex(i)
        self.theme_box.currentIndexChanged.connect(self.on_theme_changed)
        self.theme_box.setCursor(Qt.PointingHandCursor)

        # -------- Gazepoint Checkbox --------
        self.cb_gazepoint = QCheckBox("Hide GP?")
        self.cb_gazepoint.setChecked(self.gazepoint_blocked)
        self.cb_gazepoint.setObjectName("CBCheckbox")
        self.cb_gazepoint.toggled.connect(self.on_gazepoint_blocked_changed)
        self.cb_gazepoint.setCursor(Qt.PointingHandCursor)

        # -------- CAL/FIL vertical block --------
        cal_fil = make_vblock([
            make_labeled_row("CAL:", self.calibration_box),
            make_labeled_row("FIL:", self.filter_box),
        ])

        # -------- Dwell/Blink vertical block --------
        dwell_blink = make_vblock([
            make_labeled_row("Dwell:", self.dwell_spin),
            make_labeled_row("Blink:", self.blink_spin),
        ])

        # ------------- add toolbar elements here --------------
        self._add_actions([self.act_add, self.act_edit, self.act_del])
        self.tb.addSeparator()
        self._add_actions([self.act_undo, self.act_redo])
        self.tb.addSeparator()
        self._add_actions([self.act_open, self.act_save, self.act_new])
        self.tb.addSeparator()

        self.tb.addWidget(cal_fil)
        self.tb.addWidget(dwell_blink)
        self.tb.addSeparator()
        self.tb.addWidget(self.cb_gazepoint)
        self.tb.addWidget(self.theme_box)

        self.act_new.triggered.connect(self.new_json)
        self.act_open.triggered.connect(self.load_json)
        self.act_save.triggered.connect(self.save_json)
        self.act_add.triggered.connect(self.add_item)
        self.act_edit.triggered.connect(self.edit_item)
        self.act_del.triggered.connect(self.delete_item)

    def _build_ui(self):
        self.list_widget = ReorderListWidget()
        self.list_widget.setItemDelegate(CardItemDelegate(self.list_widget, get_theme=lambda: self.theme))
        self.list_widget.setWordWrap(True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setSpacing(6)

        self.list_widget.orderChanged.connect(self.on_list_reordered)
        self.list_widget.itemActivated.connect(lambda _: self.edit_item())

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)

        left = QVBoxLayout()
        left.addWidget(QLabel("Items"))
        left.addWidget(self.list_widget, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("JSON Preview"))
        right.addWidget(self.json_preview, 1)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setSpacing(14)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(left, 1)
        layout.addLayout(right, 1)
        self.setCentralWidget(root)

        self.refresh()

    # ---------- theme ----------
    def set_theme(self, theme_key: str, *, update_combo: bool = True, show_status: bool = True):
        theme_key = normalize_theme(theme_key)
        if theme_key == self.theme:
            return

        self.theme = theme_key
        apply_theme(QApplication.instance(), self.theme)

        if update_combo and hasattr(self, "theme_box"):
            set_combo_by_data(self.theme_box, self.theme)

        self.list_widget.viewport().update()
        self.refresh()

        if show_status:
            self.statusBar().showMessage(f"Theme: {THEME_NAMES[BUILDER_THEMES.index(self.theme)]}", 1200)

    def cycle_theme(self):
        order = BUILDER_THEMES
        i = order.index(self.theme) if self.theme in order else 0
        self.set_theme(order[(i + 1) % len(order)])

    def set_calibration(self, calibration_key: str, *, update_combo: bool = True, show_status: bool = True):
        if calibration_key not in CALIBRATIONS:
            calibration_key = DEFAULT_CALIBRATION
        if calibration_key == self.calibration:
            return

        self.calibration = calibration_key
        if update_combo and hasattr(self, "calibration_box"):
            set_combo_by_data(self.calibration_box, self.calibration)

        self.refresh()
        if show_status:
            self.statusBar().showMessage(f"Calibration: {self.calibration}", 1200)

    def set_filter(self, filter_key: str, *, update_combo: bool = True, show_status: bool = True):
        if filter_key not in FILTERS:
            filter_key = DEFAULT_FILTER
        if filter_key == self.filter:
            return

        self.filter = filter_key
        if update_combo and hasattr(self, "filter_box"):
            set_combo_by_data(self.filter_box, self.filter)

        self.refresh()
        if show_status:
            self.statusBar().showMessage(f"Filter: {self.filter}", 1200)

    def set_dwell_time(self, value: int, *, update_spin: bool = True):
        self.dwell_time = int(value)
        if update_spin and hasattr(self, "dwell_spin"):
            set_spin_silent(self.dwell_spin, self.dwell_time)
        self.refresh()

    def set_blink_time(self, value: int, *, update_spin: bool = True):
        self.blink_time = int(value)
        if update_spin and hasattr(self, "blink_spin"):
            set_spin_silent(self.blink_spin, self.blink_time)
        self.refresh()

    # ---------- core ----------
    def doc(self) -> dict:
        return {
            "meta": {"title": "Gaze Questionnaire", "version": self.version},
            "calibration": self.calibration,
            "filter": self.filter,
            "dwell_time": self.dwell_time,
            "blink_time": self.blink_time,
            "gazepoint_blocked": self.gazepoint_blocked,
            "theme": self.theme,
            "items": self.items,
        }

    @staticmethod
    def format_item_label(it: dict, idx: int) -> str:
        txt = (it.get("text", "") or "").replace("\n", " ").strip()
        if len(txt) > 45:
            txt = txt[:45] + "…"
        return f"{txt}"

    def refresh(self):
        selected_obj = None
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count():
            selected_obj = self.list_widget.item(row).data(Qt.UserRole)

        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, it in enumerate(self.items, 1):
            lw_item = QListWidgetItem(self.format_item_label(it, i))
            lw_item.setData(Qt.UserRole, it)
            self.list_widget.addItem(lw_item)
        self.list_widget.blockSignals(False)

        if selected_obj is not None:
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.UserRole) is selected_obj:
                    self.list_widget.setCurrentRow(i)
                    break

        if hasattr(self, "cb_gazepoint"):
            set_checkbox_silent(self.cb_gazepoint, bool(self.gazepoint_blocked))

        if hasattr(self, "calibration_box"):
            set_combo_by_data(self.calibration_box, self.calibration)

        if hasattr(self, "filter_box"):
            set_combo_by_data(self.filter_box, self.filter)

        if hasattr(self, "theme_box"):
            set_combo_by_data(self.theme_box, self.theme)

        self.json_preview.setPlainText(pretty_json(self.doc()))

    # ---------- drag&drop reorder ----------
    def on_list_reordered(self):
        old_items = list(self.items)
        new_items = [
            self.list_widget.item(i).data(Qt.UserRole)
            for i in range(self.list_widget.count())
            if isinstance(self.list_widget.item(i).data(Qt.UserRole), dict)
        ]
        if new_items == old_items:
            return
        self.undo_stack.push(ReorderItemsCommand(self, old_items, new_items))
        self.statusBar().showMessage("Reordered", 1200)

    def on_gazepoint_blocked_changed(self, checked: bool):
        self.gazepoint_blocked = bool(checked)
        self.refresh()
        self.statusBar().showMessage(f"Hide Gazepoint: {self.gazepoint_blocked}", 1500)

    def on_dwell_changed(self, value: int):
        self.set_dwell_time(value, update_spin=False)
        self.statusBar().showMessage(f"Dwell Threshold: {self.dwell_time}", 1500)

    def on_blink_changed(self, value: int):
        self.set_blink_time(value, update_spin=False)
        self.statusBar().showMessage(f"Blink Threshold: {self.blink_time}", 1500)

    def on_theme_changed(self, _index: int):
        theme_key = self.theme_box.currentData() or "clinical"
        self.set_theme(theme_key)

    def on_calibration_changed(self, _index: int):
        calibration_key = self.calibration_box.currentData()
        self.set_calibration(calibration_key or DEFAULT_CALIBRATION)
        self.statusBar().showMessage(f"Calibration: {self.calibration}", 1500)

    def on_filter_changed(self, _index: int):
        filter_key = self.filter_box.currentData()
        self.set_filter(filter_key or DEFAULT_FILTER)
        self.statusBar().showMessage(f"Filter: {self.filter}", 1500)

    # ---------- actions ----------
    def add_item(self):
        dlg = ItemEditorDialog(self)
        if dlg.exec():
            item = dlg.get_item()
            self.undo_stack.push(AddItemCommand(self, item, index=len(self.items)))
            self.statusBar().showMessage("Item added", 1500)

    def edit_item(self):
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self.items)):
            return
        old_item = self.items[row]
        dlg = ItemEditorDialog(self, old_item)
        if dlg.exec():
            new_item = dlg.get_item()
            self.undo_stack.push(EditItemCommand(self, row, old_item, new_item))
            self.statusBar().showMessage("Item updated", 1500)

    def delete_item(self):
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        self.undo_stack.push(DeleteItemCommand(self, row, item))
        self.statusBar().showMessage("Item deleted", 1500)

    def new_json(self):
        self.items = []
        self.gazepoint_blocked = False
        self.current_path = None
        self.filename = "*"
        self.update_window_title()
        self.refresh()
        self.statusBar().showMessage("New document", 1500)
        self.undo_stack.clear()

    def save_json(self):
        if self.current_path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "demo.json", "JSON (*.json)")
            if not path:
                return
            self.current_path = Path(path)
            self.filename = self.current_path.name
            self.update_window_title()

        try:
            self.current_path.write_text(pretty_json(self.doc()), encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return

        self.statusBar().showMessage("Saved", 1500)
        self.undo_stack.clear()

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load JSON", "", "JSON (*.json)")
        if not path:
            return

        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.filename = str(Path(path).name)
            self.update_window_title()

        except Exception as e:
            QMessageBox.warning(self, "Invalid JSON", f"Could not parse JSON:\n{e}")
            return

        items = data.get("items")
        if not isinstance(items, list):
            QMessageBox.warning(self, "Invalid JSON", "Missing 'items' list.")
            return

        gp = data.get("gazepoint_blocked", False)
        if isinstance(gp, str):
            gp = gp.strip().lower() in ("true", "1", "yes")
        self.gazepoint_blocked = bool(gp)

        self.set_theme(data.get("theme", DEFAULT_THEME), show_status=False)
        self.set_calibration(data.get("calibration", DEFAULT_CALIBRATION), show_status=False)
        self.set_filter(data.get("filter", DEFAULT_FILTER), show_status=False)
        self.set_dwell_time(int(data.get("dwell_time", DEFAULT_DWELL_TIME)))
        self.set_blink_time(int(data.get("blink_time", DEFAULT_BLINK_TIME)))

        self.items = items
        self.current_path = Path(path)
        self.refresh()
        self.statusBar().showMessage("Loaded", 1500)

# ------------------ main ------------------

def run():
    app = QApplication([])
    win = BuilderMainWindow()
    win.show()
    app.exec()

if __name__ == "__main__":
    run()
