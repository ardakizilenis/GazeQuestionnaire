#!/usr/bin/env python3
import json
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QComboBox, QSpinBox,
    QFileDialog, QMessageBox, QFormLayout, QDialog, QDialogButtonBox,
    QLabel, QToolBar, QStyle, QStyledItemDelegate, QCheckBox
)


QUESTION_TYPES = ["info", "yesno", "mcq", "likert", "textgrid", "sp_yesno", "sp_mcq", "sp_likert"]
ACTIVATIONS = ["dwell", "blink"]


# ------------------ helpers ------------------

def pretty_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)

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

def light_stylesheet() -> str:
    return """
    QWidget {
        background-color: #f6f7fb;
        color: #111827;
        font-size: 14px;
    }
    QLabel { font-weight: 700; }

    QToolBar {
        background: #ffffff;
        border-bottom: 1px solid #e5e7eb;
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 8px;
        padding: 6px;
    }
    QToolButton:hover { background: #f3f4f6; }
    QToolButton:pressed { background: #e5e7eb; }

    QListWidget {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
    }
    QListWidget::item { padding: 8px; }
    QListWidget::item:selected {
        background: transparent;
        color: #111827;
        border-radius: 6px;
    }

    QTextEdit {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 6px;
        min-height: 30px;
    }

    QStatusBar {
        background: #ffffff;
        border-top: 1px solid #e5e7eb;
    }

    QDialog { background: #ffffff; }
    """


def dark_stylesheet() -> str:
    return """
    QWidget {
        background-color: #1e1e1e;
        color: #eaeaea;
        font-size: 14px;
    }
    QLabel { font-weight: 700; }

    QToolBar {
        background: #252526;
        border-bottom: 1px solid #333;
        spacing: 6px;
        padding: 6px;
    }
    QToolButton {
        background: transparent;
        border-radius: 8px;
        padding: 6px;
    }
    QToolButton:hover { background: #333333; }
    QToolButton:pressed { background: #3c3c3c; }

    QListWidget {
        background: transparent;
        border: 1px solid #333;
        border-radius: 10px;
    }
    QListWidget::item { padding: 8px; }
    QListWidget::item:selected { background: #094771; }

    QTextEdit {
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 8px;
        font-family: Consolas, Courier, monospace;
        font-size: 12px;
    }

    QComboBox, QSpinBox {
        background: #2d2d2d;
        border: 1px solid #3c3c3c;
        border-radius: 8px;
        padding: 6px;
        min-height: 30px;
    }

    QStatusBar {
        background: #252526;
        border-top: 1px solid #333;
    }

    QDialog { background: #252526; }
    """

def type_colors(theme: str) -> dict:
    if theme == "neon":
        # Futuristic / neon palette (matches your smooth-pursuit neon vibe)
        return {
            "info":     {"bg": "#0F1838", "accent": "#66F0FF", "fg": "#EAF2FF"},
            "yesno":    {"bg": "#0F172A", "accent": "#3B82F6", "fg": "#EAF2FF"},
            "mcq":      {"bg": "#071A18", "accent": "#39FF9A", "fg": "#EAF2FF"},
            "likert":   {"bg": "#1B0B22", "accent": "#FF4FD8", "fg": "#FFE6FB"},
            "textgrid": {"bg": "#231A05", "accent": "#F59E0B", "fg": "#FFF7ED"},
            "sp_yesno": {"bg": "#0B1330", "accent": "#9B7CFF", "fg": "#EAF2FF"},
            "sp_mcq":   {"bg": "#0B1330", "accent": "#39FF9A", "fg": "#EAF2FF"},
            "sp_likert":{"bg": "#0B1330", "accent": "#FB7185", "fg": "#FFE4E6"},
        }

    if theme == "dark":
        return {
            "info":     {"bg": "#1f2937", "accent": "#60a5fa", "fg": "#e5e7eb"},
            "yesno":    {"bg": "#172554", "accent": "#3b82f6", "fg": "#e5e7eb"},
            "mcq":      {"bg": "#14532d", "accent": "#22c55e", "fg": "#e5e7eb"},
            "likert":   {"bg": "#3f1d2f", "accent": "#f472b6", "fg": "#fce7f3"},
            "textgrid": {"bg": "#3b2f0b", "accent": "#f59e0b", "fg": "#fff7ed"},
            "sp_yesno": {"bg": "#0f172a", "accent": "#a78bfa", "fg": "#e5e7eb"},
            "sp_mcq":   {"bg": "#0f172a", "accent": "#34d399", "fg": "#e5e7eb"},
            "sp_likert":{"bg": "#0f172a", "accent": "#fb7185", "fg": "#ffe4e6"},
        }

    # light
    return {
        "info":     {"bg": "#eef2ff", "accent": "#2563eb", "fg": "#111827"},
        "yesno":    {"bg": "#eff6ff", "accent": "#1d4ed8", "fg": "#111827"},
        "mcq":      {"bg": "#ecfdf5", "accent": "#16a34a", "fg": "#064e3b"},
        "likert":   {"bg": "#fdf2f8", "accent": "#db2777", "fg": "#111827"},
        "textgrid": {"bg": "#fffbeb", "accent": "#d97706", "fg": "#111827"},
        "sp_yesno": {"bg": "#f5f3ff", "accent": "#7c3aed", "fg": "#111827"},
        "sp_mcq":   {"bg": "#ecfdf5", "accent": "#059669", "fg": "#064e3b"},
        "sp_likert":{"bg": "#fff1f2", "accent": "#e11d48", "fg": "#111827"},
    }


def apply_theme(app: QApplication, mode: str):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 11))

    if mode == "dark":
        app.setStyleSheet(dark_stylesheet())
    elif mode == "neon":
        app.setStyleSheet(neon_stylesheet())
    else:
        app.setStyleSheet(light_stylesheet())


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

    def dropEvent(self, event):
        super().dropEvent(event)
        self.orderChanged.emit()


# ------------------ Item Editor ------------------

class CardItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, get_theme=lambda: "dark"):
        super().__init__(parent)
        self.get_theme = get_theme

    def paint(self, painter: QPainter, option, index):
        painter.save()

        theme = self.get_theme()
        palette = type_colors(theme)

        it = index.data(Qt.UserRole) or {}
        qtype = it.get("type", "info")
        c = palette.get(qtype, palette["info"])

        # Full-width rect inside viewport with margins
        r = option.rect.adjusted(10, 6, -10, -6)

        bg = QColor(c["bg"])
        fg = QColor(c["fg"])
        accent = QColor(c["accent"])

        # Selection / hover
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        if selected:
            border = QColor(accent)
            border.setAlpha(230)
        elif hovered:
            border = QColor(accent if theme == "neon" else "#000000")
            border.setAlpha(140 if theme == "neon" else 45)
        else:
            border = QColor("#000000")
            border.setAlpha(22 if theme == "neon" else (35 if theme == "dark" else 25))

        painter.setRenderHint(QPainter.Antialiasing, True)

        # Card background + border
        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(r, 10, 10)

        # Accent stripe (left)
        stripe = r.adjusted(0, 0, -r.width() + 6, 0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(stripe, 10, 10)

        # Text
        text = index.data(Qt.DisplayRole) or ""
        text_rect = r.adjusted(14, 10, -10, -10)
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

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 999)
        self.duration_spin.setValue(5)

        self.labels_edit = QTextEdit()
        self.labels_edit.setPlaceholderText("One label per line.\nMCQ = 4 lines, Likert = 5 lines.")

        self.activation_row = QWidget()
        act_layout = QHBoxLayout(self.activation_row)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.addWidget(self.activation_box)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.addRow("Type", self.type_box)
        form.addRow("Activation", self.activation_row)
        form.addRow("Text", self.text_edit)
        form.addRow("Duration (info)", self.duration_spin)
        form.addRow("Labels", self.labels_edit)

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
        self.duration_spin.setEnabled(qtype == "info")
        self.activation_row.setVisible(qtype not in ("info", "sp_yesno", "sp_mcq", "sp_likert"))
        self.labels_edit.setEnabled(qtype in ("mcq", "likert", "sp_mcq", "sp_likert"))

    def _load(self, it: dict):
        self.type_box.setCurrentText(it.get("type", "info"))
        self.text_edit.setPlainText(it.get("text", ""))
        if it.get("activation") in ACTIVATIONS:
            self.activation_box.setCurrentText(it["activation"])
        self.duration_spin.setValue(int(it.get("duration", 5) or 5))
        labels = it.get("labels", [])
        if isinstance(labels, list):
            self.labels_edit.setPlainText("\n".join(str(x) for x in labels))

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
            it["labels"] = [l.strip() for l in self.labels_edit.toPlainText().splitlines() if l.strip()]
            return it

        it["activation"] = self.activation_box.currentText()

        if qtype in ("mcq", "likert"):
            it["labels"] = [l.strip() for l in self.labels_edit.toPlainText().splitlines() if l.strip()]

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


# ------------------ Main Window ------------------

class BuilderMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1120, 680)

        self.items: list[dict] = []
        self.current_path: Path | None = None
        self.gazepoint_blocked: bool = False

        self.theme = "light"  # default
        apply_theme(QApplication.instance(), self.theme)

        self._build_toolbar()
        self._build_ui()

        self.statusBar().showMessage("Ready")

    # ---------- UI ----------
    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)

        st = self.style()

        self.act_new = QAction(st.standardIcon(QStyle.SP_FileIcon), "New", self)
        self.act_open = QAction(st.standardIcon(QStyle.SP_DialogOpenButton), "Open", self)
        self.act_save = QAction(st.standardIcon(QStyle.SP_DialogSaveButton), "Save", self)

        self.act_add = QAction(st.standardIcon(QStyle.SP_FileDialogNewFolder), "Add", self)
        self.act_edit = QAction(st.standardIcon(QStyle.SP_DesktopIcon), "Edit", self)
        self.act_del = QAction(st.standardIcon(QStyle.SP_TrashIcon), "Delete", self)

        self.act_new.setShortcut("Ctrl+N")
        self.act_open.setShortcut("Ctrl+O")
        self.act_save.setShortcut("Ctrl+S")
        self.act_del.setShortcut("Backspace")

        # Theme toggle
        self.icon_sun = self.style().standardIcon(QStyle.SP_DialogYesButton)
        self.icon_moon = self.style().standardIcon(QStyle.SP_DialogNoButton)
        self.act_theme = QAction(self.icon_moon, "Dark mode", self)
        self.act_theme = QAction(self.icon_moon, "Theme: Light", self)
        tb.addAction(self.act_theme)

        self.cb_gazepoint = QCheckBox("Block Gazepoint?")
        self.cb_gazepoint.setChecked(self.gazepoint_blocked)
        self.cb_gazepoint.toggled.connect(self.on_gazepoint_blocked_changed)

        tb.addAction(self.act_new)
        tb.addAction(self.act_open)
        tb.addAction(self.act_save)
        tb.addSeparator()
        tb.addAction(self.act_add)

        tb.addAction(self.act_edit)
        tb.addAction(self.act_del)
        tb.addSeparator()
        tb.addAction(self.act_theme)
        tb.addWidget(self.cb_gazepoint)

        self.act_new.triggered.connect(self.new_json)
        self.act_open.triggered.connect(self.load_json)
        self.act_save.triggered.connect(self.save_json)
        self.act_add.triggered.connect(self.add_item)
        self.act_edit.triggered.connect(self.edit_item)
        self.act_del.triggered.connect(self.delete_item)
        self.act_theme.triggered.connect(self.cycle_theme)

    def _build_ui(self):
        self.list_widget = ReorderListWidget()
        self.list_widget.setItemDelegate(CardItemDelegate(self.list_widget, get_theme=lambda: self.theme))
        self.list_widget.setWordWrap(True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setSpacing(6)

        self.list_widget.orderChanged.connect(self.on_list_reordered)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.edit_item())

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.list_widget.setMouseTracking(True)

        left = QVBoxLayout()
        left.addWidget(QLabel("Items"))
        left.addWidget(self.list_widget)

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
    def toggle_theme(self, checked: bool):
        if checked:
            self.theme = "dark"
            self.act_theme.setIcon(self.icon_sun)
            self.act_theme.setText("Light mode")
        else:
            self.theme = "light"
            self.act_theme.setIcon(self.icon_moon)
            self.act_theme.setText("Dark mode")

        apply_theme(QApplication.instance(), self.theme)
        self.statusBar().showMessage(f"Theme: {self.theme}", 1200)

    def cycle_theme(self):
        order = ["light", "dark", "neon"]
        i = order.index(self.theme) if self.theme in order else 0
        self.theme = order[(i + 1) % len(order)]

        # icon + label
        if self.theme == "light":
            self.act_theme.setIcon(self.icon_moon)
            self.act_theme.setText("Theme: Light")
        elif self.theme == "dark":
            self.act_theme.setIcon(self.icon_sun)
            self.act_theme.setText("Theme: Dark")
        else:
            # neon: use something noticeable (reuse an icon, or set a custom one if you have it)
            self.act_theme.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            self.act_theme.setText("Theme: Neon")

        apply_theme(QApplication.instance(), self.theme)
        self.list_widget.viewport().update()
        self.statusBar().showMessage(f"Theme: {self.theme}", 1200)

    # ---------- core ----------
    def doc(self) -> dict:
        return \
            {
                "meta":
                    {
                        "title": "Gaze Questionnaire",
                        "version": 1
                    },
                "gazepoint_blocked": self.gazepoint_blocked,
                "items":
                    self.items
            }

    @staticmethod
    def format_item_label(it: dict, idx: int) -> str:
        qtype = it.get("type", "?")
        txt = (it.get("text", "") or "").replace("\n", " ")
        if len(txt) > 70:
            txt = txt[:70] + "…"

        if qtype == "info":
            return f"{idx:02d}. [info {it.get('duration', 5)}s] {txt}"
        if qtype == "sp_yesno":
            return f"{idx:02d}. [sp_yesno] {txt}"
        if qtype == "sp_mcq":
            return f"{idx:02d}. [sp_mcq] {txt}"
        if qtype == "sp_likert":
            return f"{idx:02d}. [sp_likert] {txt}"
        act = it.get("activation", "")
        return f"{idx:02d}. [{qtype} | {act}] {txt}"

    def refresh(self):
        # selection-by-object (dict identity) behalten
        selected_obj = None
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count():
            selected_obj = self.list_widget.item(row).data(Qt.UserRole)

        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, it in enumerate(self.items, 1):
            item = QListWidgetItem(self.format_item_label(it, i))
            item.setData(Qt.UserRole, it)  # pointer to dict
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

        # restore selection if possible
        if selected_obj is not None:
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.UserRole) is selected_obj:
                    self.list_widget.setCurrentRow(i)
                    break
        if hasattr(self, "cb_gazepoint"):
            self.cb_gazepoint.blockSignals(True)
            self.cb_gazepoint.setChecked(bool(self.gazepoint_blocked))
            self.cb_gazepoint.blockSignals(False)

        self.json_preview.setPlainText(pretty_json(self.doc()))

    # ---------- drag&drop reorder ----------
    def on_list_reordered(self):
        # after DnD, rebuild items from current list order (UserRole points to dicts)
        new_items = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i).data(Qt.UserRole)
            if isinstance(it, dict):
                new_items.append(it)
        self.items = new_items
        self.refresh()
        self.statusBar().showMessage("Reordered", 1200)

    def on_gazepoint_blocked_changed(self, checked: bool):
        self.gazepoint_blocked = bool(checked)
        self.refresh()
        self.save_json()
        self.statusBar().showMessage(f"Blocked Gazepoint: {self.gazepoint_blocked}", 1500)

    # ---------- actions ----------
    def add_item(self):
        dlg = ItemEditorDialog(self)
        if dlg.exec():
            self.items.append(dlg.get_item())
            self.refresh()
            self.list_widget.setCurrentRow(len(self.items) - 1)
            self.save_json()
            self.statusBar().showMessage("Item added", 1500)

    def edit_item(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.items):
            return
        dlg = ItemEditorDialog(self, self.items[row])
        if dlg.exec():
            self.items[row] = dlg.get_item()
            self.refresh()
            self.list_widget.setCurrentRow(row)
            self.save_json()
            self.statusBar().showMessage("Item updated", 1500)

    def delete_item(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.items):
            return
        del self.items[row]
        self.refresh()
        self.save_json()
        self.statusBar().showMessage("Item deleted", 1500)

    def new_json(self):
        self.items = []
        self.gazepoint_blocked = False
        self.current_path = None
        self.refresh()
        self.statusBar().showMessage("New document", 1500)

    def save_json(self):
        doc = self.doc()

        if self.current_path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "questionnaire.json", "JSON (*.json)")
            if not path:
                return
            self.current_path = Path(path)

        try:
            self.current_path.write_text(pretty_json(doc), encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return

        self.statusBar().showMessage("Saved", 1500)

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load JSON", "", "JSON (*.json)")
        if not path:
            return

        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
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

        self.items = items
        self.current_path = Path(path)
        self.refresh()
        self.statusBar().showMessage("Loaded", 1500)

# ------------------ main ------------------

if __name__ == "__main__":
    app = QApplication([])
    # default theme will be applied by the window (dark)
    win = BuilderMainWindow()
    win.show()
    app.exec()
