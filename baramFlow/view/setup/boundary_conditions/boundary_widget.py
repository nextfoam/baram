#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPoint

from baramFlow.coredb.boundary_db import BoundaryDB
from .boundary_widget_ui import Ui_BoundaryWidget


class BoundaryWidget(QWidget):
    rightClicked = Signal(int, QPoint)

    def __init__(self, rname, bcid, bcname, bctype, parent):
        super().__init__()
        self._ui = Ui_BoundaryWidget()
        self._ui.setupUi(self)

        self._rname = rname
        self._bcid = bcid
        self._bcname = bcname
        self._bctype = None
        self._parent = parent

        self._ui.name.setText(bcname)
        self._setType(bctype)

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self._connectSignalsSlots()

    @property
    def rname(self):
        return self._rname

    @property
    def bctype(self):
        return self._bctype

    @property
    def bcname(self):
        return self._bcname

    @property
    def parent(self):
        return self._parent

    def reloadType(self):
        self._setType(BoundaryDB.getBoundaryType(self._bcid))

    def _setType(self, bctype):
        self._bctype = bctype
        self._ui.type.setText(BoundaryDB.dbBoundaryTypeToText(bctype))

    def _connectSignalsSlots(self):
        self.customContextMenuRequested.connect(self._popupRequested)

    def _popupRequested(self, point):
        self.rightClicked.emit(self._bcid, self.mapToGlobal(point))
