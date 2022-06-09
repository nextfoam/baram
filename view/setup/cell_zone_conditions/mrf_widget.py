#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from view.setup.boundary_conditions.boundary_db import BoundaryDB
from view.widgets.multi_selector_dialog import MultiSelectorDialog
from .mrf_widget_ui import Ui_MRFWidget


class MRFWidget(QWidget):
    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_MRFWidget()
        self._ui.setupUi(self)
        self.setVisible(False)

        self._db = coredb.CoreDB()
        self._xpath = xpath + '/mrf'

        self._dialog = None

        self._connectSignalsSlots()

    def load(self):
        self._ui.rotatingSpeed.setText(self._db.getValue(self._xpath + '/rotatingSpeed'))
        self._ui.rotationAxisOriginX.setText(self._db.getValue(self._xpath + '/rotationAxisOrigin/x'))
        self._ui.rotationAxisOriginY.setText(self._db.getValue(self._xpath + '/rotationAxisOrigin/y'))
        self._ui.rotationAxisOriginZ.setText(self._db.getValue(self._xpath + '/rotationAxisOrigin/z'))
        self._ui.rotationAxisDirectionX.setText(self._db.getValue(self._xpath + '/rotationAxisDirection/x'))
        self._ui.rotationAxisDirectionY.setText(self._db.getValue(self._xpath + '/rotationAxisDirection/y'))
        self._ui.rotationAxisDirectionZ.setText(self._db.getValue(self._xpath + '/rotationAxisDirection/z'))
        self._staticBoundaries = self._db.getValue(self._xpath + '/staticBoundaries')
        self._setStaticBoundaryList(self._staticBoundaries.split() if self._staticBoundaries else [])

    def appendToWriter(self, writer):
        writer.append(self._xpath + '/rotatingSpeed',
                      self._ui.rotatingSpeed.text(), self.tr("Rotating Speed"))
        writer.append(self._xpath + '/rotationAxisOrigin/x',
                      self._ui.rotationAxisOriginX.text(), self.tr("Rotating-Axis Origin X"))
        writer.append(self._xpath + '/rotationAxisOrigin/y',
                      self._ui.rotationAxisOriginY.text(), self.tr("Rotating-Axis Origin Y"))
        writer.append(self._xpath + '/rotationAxisOrigin/z',
                      self._ui.rotationAxisOriginZ.text(), self.tr("Rotating-Axis Origin Z"))
        writer.append(self._xpath + '/rotationAxisDirection/x',
                      self._ui.rotationAxisDirectionX.text(), self.tr("Rotating-Axis Direction X"))
        writer.append(self._xpath + '/rotationAxisDirection/y',
                      self._ui.rotationAxisDirectionY.text(), self.tr("Rotating-Axis Direction Y"))
        writer.append(self._xpath + '/rotationAxisDirection/z',
                      self._ui.rotationAxisDirectionZ.text(), self.tr("Rotating-Axis Direction Z"))

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectStaticBoundaries)

    def _setStaticBoundaryList(self, boundaries):
        self._ui.staticBoundary.clear()
        for i in boundaries:
            # name = self._db.getValue(BoundaryDB.getBoundaryXPath(i) + '/name')
            # region = self._db.getValue(BoundaryDB.getBoundaryXPath(i) + '/../../name')
            # self._ui.staticBoundary.addItem(f'{name} - {region}')
            self._ui.staticBoundary.addItem(f'{i}')

    def _selectStaticBoundaries(self):
        self._dialog = MultiSelectorDialog(self,self.tr("Select Boundaries"),
                                                   BoundaryDB.getBoundariesForSelector(), self._staticBoundaries)
        self._dialog.open()
        self._dialog.accepted.connect(self._staticBoundariesChanged)

    def _staticBoundariesChanged(self):
        boundaries = self._dialog.selectedItems()
        self._setStaticBoundaryList(boundaries)
        self._staticBoundaries = ' '.join(boundaries)
