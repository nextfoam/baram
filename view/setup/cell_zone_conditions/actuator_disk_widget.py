#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .actuator_disk_widget_ui import Ui_ActuatorDiskWidget


class ActuatorDiskWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ActuatorDiskWidget()
        self._ui.setupUi(self)
        self.setVisible(False)
