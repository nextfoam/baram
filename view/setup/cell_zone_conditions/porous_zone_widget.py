#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .porous_zone_widget_ui import Ui_porousZoneWidget


class PorousZoneWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_porousZoneWidget()
        self._ui.setupUi(self)
        self.setVisible(False)
