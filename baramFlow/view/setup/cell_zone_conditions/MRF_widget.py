#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.widgets.multi_selector_dialog import MultiSelectorDialog
from .MRF_widget_ui import Ui_MRFWidget


class MRFWidget(QWidget):
    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_MRFWidget()
        self._ui.setupUi(self)
        self.setVisible(False)

        self._staticBoundaries = None
        self._xpath = xpath + '/mrf'
        self._dialog = None

        self._connectSignalsSlots()

    def load(self):
        db = coredb.CoreDB()
        self._ui.rotatingSpeed.setText(db.getValue(self._xpath + '/rotatingSpeed'))
        self._ui.rotationAxisOriginX.setText(db.getValue(self._xpath + '/rotationAxisOrigin/x'))
        self._ui.rotationAxisOriginY.setText(db.getValue(self._xpath + '/rotationAxisOrigin/y'))
        self._ui.rotationAxisOriginZ.setText(db.getValue(self._xpath + '/rotationAxisOrigin/z'))
        self._ui.rotationAxisDirectionX.setText(db.getValue(self._xpath + '/rotationAxisDirection/x'))
        self._ui.rotationAxisDirectionY.setText(db.getValue(self._xpath + '/rotationAxisDirection/y'))
        self._ui.rotationAxisDirectionZ.setText(db.getValue(self._xpath + '/rotationAxisDirection/z'))
        boundaries = db.getValue(self._xpath + '/staticBoundaries')
        self._setStaticBoundaries(boundaries.split() if boundaries else [])

    def updateDB(self, newDB):
        newDB.setValue(self._xpath + '/rotatingSpeed', self._ui.rotatingSpeed.text(), self.tr("Rotating Speed"))
        newDB.setValue(self._xpath + '/rotationAxisOrigin/x', self._ui.rotationAxisOriginX.text(),
                    self.tr("Rotating-Axis Origin X"))
        newDB.setValue(self._xpath + '/rotationAxisOrigin/y', self._ui.rotationAxisOriginY.text(),
                    self.tr("Rotating-Axis Origin Y"))
        newDB.setValue(self._xpath + '/rotationAxisOrigin/z', self._ui.rotationAxisOriginZ.text(),
                    self.tr("Rotating-Axis Origin Z"))
        newDB.setValue(self._xpath + '/rotationAxisDirection/x', self._ui.rotationAxisDirectionX.text(),
                    self.tr("Rotating-Axis Direction X"))
        newDB.setValue(self._xpath + '/rotationAxisDirection/y', self._ui.rotationAxisDirectionY.text(),
                    self.tr("Rotating-Axis Direction Y"))
        newDB.setValue(self._xpath + '/rotationAxisDirection/z', self._ui.rotationAxisDirectionZ.text(),
                    self.tr("Rotating-Axis Direction Z"))
        newDB.setValue(self._xpath + '/staticBoundaries', ' '.join(b for b in self._staticBoundaries),
                    self.tr("Static Boundary"))

        return True

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectStaticBoundaries)

    def _setStaticBoundaries(self, boundaries):
        self._staticBoundaries = boundaries

        self._ui.staticBoundary.clear()
        for b in boundaries:
            self._ui.staticBoundary.addItem(BoundaryDB.getBoundaryText(b))

    def _selectStaticBoundaries(self):
        self._dialog = MultiSelectorDialog(self, self.tr("Select Boundaries"), BoundaryDB.getBoundarySelectorItems(),
                                           self._staticBoundaries)
        self._dialog.accepted.connect(self._staticBoundariesChanged)
        self._dialog.open()

    def _staticBoundariesChanged(self):
        boundaries = self._dialog.selectedItems()
        self._setStaticBoundaries(boundaries)
