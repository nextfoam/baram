#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from .sliding_mesh_widget_ui import Ui_SlidingMeshWidget


class SlidingMeshWidget(QWidget):
    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_SlidingMeshWidget()
        self._ui.setupUi(self)
        self.setVisible(False)

        self._xpath = xpath + '/slidingMesh'

    def load(self):
        db = coredb.CoreDB()
        self._ui.rotatingSpeed.setText(db.getValue(self._xpath + '/rotatingSpeed'))
        self._ui.rotationAxisOriginX.setText(db.getValue(self._xpath + '/rotationAxisOrigin/x'))
        self._ui.rotationAxisOriginY.setText(db.getValue(self._xpath + '/rotationAxisOrigin/y'))
        self._ui.rotationAxisOriginZ.setText(db.getValue(self._xpath + '/rotationAxisOrigin/z'))
        self._ui.rotationAxisDirectionX.setText(db.getValue(self._xpath + '/rotationAxisDirection/x'))
        self._ui.rotationAxisDirectionY.setText(db.getValue(self._xpath + '/rotationAxisDirection/y'))
        self._ui.rotationAxisDirectionZ.setText(db.getValue(self._xpath + '/rotationAxisDirection/z'))

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

        return True
