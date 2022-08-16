#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout

from .monitors_page_ui import Ui_MonitorsPage
from .forces_widget import ForcesWidget
from .points_widget import PointsWidget
from .surfaces_widget import SurfacesWidget
from .volumes_widget import VolumesWidget


class MonitorsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MonitorsPage()
        self._ui.setupUi(self)

        self._forcesWidget = ForcesWidget()
        self._pointsWidget = PointsWidget()
        self._surfacesWidget = SurfacesWidget()
        self._volumesWidget = VolumesWidget()

        layout = QVBoxLayout(self._ui.monitors)
        layout.addWidget(self._forcesWidget)
        layout.addWidget(self._pointsWidget)
        layout.addWidget(self._surfacesWidget)
        layout.addWidget(self._volumesWidget)
        layout.addStretch()

    def save(self):
        pass

    def load(self):
        pass

    def clear(self):
        self._forcesWidget.clear()
        self._pointsWidget.clear()
        self._surfacesWidget.clear()
        self._volumesWidget.clear()
