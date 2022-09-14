#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPoint

from coredb import coredb
from coredb.boundary_db import BoundaryDB
from .boundary_widget_ui import Ui_BoundaryWidget


class BoundaryWidget(QWidget):
    rightClicked = Signal(int, QPoint)

    def __init__(self, bcid, bcname, bctype):
        super().__init__()
        self._ui = Ui_BoundaryWidget()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._bcid = bcid
        self.bctype = bctype
        self._bcname = bcname

        self._ui.name.setText(bcname)

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self._connectSignalsSlots()

    @property
    def bctype(self):
        return self._bctype

    @property
    def bcname(self):
        return self._bcname

    @bctype.setter
    def bctype(self, bctype):
        self._bctype = bctype
        self._ui.type.setText(BoundaryDB.dbBoundaryTypeToText(bctype))

    def reloadType(self):
        self.bctype = BoundaryDB.getBoundaryType(self._bcid)

    def _connectSignalsSlots(self):
        self.customContextMenuRequested.connect(self._popupRequested)

    def _popupRequested(self, point):
        self.rightClicked.emit(self._bcid, self.mapToGlobal(point))
