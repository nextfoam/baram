#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPoint

from baramFlow.coredb.boundary_db import BoundaryDB
from .boundary_widget_ui import Ui_BoundaryWidget


class BoundaryWidget(QWidget):
    rightClicked = Signal(int, QPoint)

    def __init__(self, rname, bcid, bcname, bctype):
        super().__init__()
        self._ui = Ui_BoundaryWidget()
        self._ui.setupUi(self)

        self._rname = rname
        self._bcid = bcid
        self._bctype = None

        self._ui.name.setText(bcname)
        self.setType(bctype)

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self._connectSignalsSlots()

    @property
    def rname(self):
        return self._rname

    @property
    def bcid(self):
        return self._bcid

    def bcname(self):
        return self._ui.name.text()

    def type(self):
        return self._bctype

    def setType(self, bctype):
        self._bctype = bctype
        self._ui.type.setText(BoundaryDB.dbBoundaryTypeToText(bctype))

    def _connectSignalsSlots(self):
        self.customContextMenuRequested.connect(self._popupRequested)

    def _popupRequested(self, point):
        self.rightClicked.emit(self._bcid, self.mapToGlobal(point))
