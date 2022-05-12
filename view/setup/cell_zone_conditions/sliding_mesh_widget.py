#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .sliding_mesh_widget_ui import Ui_SlidingMeshWidget


class SlidingMeshWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_SlidingMeshWidget()
        self._ui.setupUi(self)
        self.setVisible(False)
