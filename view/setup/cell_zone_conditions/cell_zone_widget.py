#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, QPoint

from coredb import coredb
from .cell_zone_widget_ui import Ui_CellZoneWidget


class CellZoneWidget(QWidget):
    rightClicked = Signal(int, QPoint)

    def __init__(self, czid, czname):
        super().__init__()
        self._ui = Ui_CellZoneWidget()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._czid = czid

        self._ui.name.setText(czname)
        self._ui.type.setVisible(False)
