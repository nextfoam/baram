#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.monitor_db import MonitorDB, DirectionSpecificationMethod
from baramFlow.view.widgets.region_objects_selector import BoundariesSelector

from .contour_dialog_ui import Ui_ContourDialog


class ContourDialog(QDialog):
    def __init__(self, parent, name=None):
        super().__init__(parent)

        self._ui = Ui_ContoursDialog()
        self._ui.setupUi(self)

        self._name = name

        self._connectSignalsSlots()

        self._load()

    def getName(self):
        return self._name

    def accept(self):
        super().accept()

    def reject(self):
        super().reject()

    def _connectSignalsSlots(self):
        pass

    def _load(self):

    def _setBoundaries(self, boundaries):
        self._boundaries = boundaries

        self._ui.boundaries.clear()
        for bcid in boundaries:
            self._ui.boundaries.addItem(BoundaryDB.getBoundaryText(bcid))

    def _selectBoundaries(self):
        self._dialog = BoundariesSelector(self, self._boundaries)
        self._dialog.accepted.connect(self._boundariesChanged)
        self._dialog.open()

    def _boundariesChanged(self):
        self._region = self._dialog.region()
        self._setBoundaries(self._dialog.selectedItems())

    def _specificationMethodChanged(self, method):
        if method == DirectionSpecificationMethod.DIRECT:
            self._ui.direction.setTitle(self.tr('Direction'))
            self._ui.angles.hide()
        else:
            self._ui.direction.setTitle(self.tr('Direction at AOA=0, AOS=0'))
            self._ui.angles.show()
