# ui/gaze_widget.py
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Slot


class GazeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gaze_x = None
        self.gaze_y = None
        self.screen_width = 1700
        self.screen_height = 1000
        self.point_radius = 10

    # setter for gaze
    @Slot(float, float)
    def set_gaze(self, x, y):
        self.gaze_x = x
        self.gaze_y = y
        self.update()

    # maps the calibrated gaze to the UI/Widget
    def map_gaze_to_widget(self):
        if self.gaze_x is None or self.gaze_y is None:
            return None, None
        draw_x = (self.gaze_x / self.screen_width) * self.width()
        draw_y = (self.gaze_y / self.screen_height) * self.height()
        return int(draw_x), int(draw_y)
