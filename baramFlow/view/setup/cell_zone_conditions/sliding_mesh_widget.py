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

        self._db = coredb.CoreDB()
        self._xpath = xpath + '/slidingMesh'

    def load(self):
        self._ui.rotatingSpeed.setText(self._db.getValue(self._xpath + '/rotatingSpeed'))
        self._ui.rotationAxisOriginX.setText(self._db.getValue(self._xpath + '/rotationAxisOrigin/x'))
        self._ui.rotationAxisOriginY.setText(self._db.getValue(self._xpath + '/rotationAxisOrigin/y'))
        self._ui.rotationAxisOriginZ.setText(self._db.getValue(self._xpath + '/rotationAxisOrigin/z'))
        self._ui.rotationAxisDirectionX.setText(self._db.getValue(self._xpath + '/rotationAxisDirection/x'))
        self._ui.rotationAxisDirectionY.setText(self._db.getValue(self._xpath + '/rotationAxisDirection/y'))
        self._ui.rotationAxisDirectionZ.setText(self._db.getValue(self._xpath + '/rotationAxisDirection/z'))

    def updateDB(self, db):
        db.setValue(self._xpath + '/rotatingSpeed', self._ui.rotatingSpeed.text(), self.tr("Rotating Speed"))
        db.setValue(self._xpath + '/rotationAxisOrigin/x', self._ui.rotationAxisOriginX.text(),
                    self.tr("Rotating-Axis Origin X"))
        db.setValue(self._xpath + '/rotationAxisOrigin/y', self._ui.rotationAxisOriginY.text(),
                    self.tr("Rotating-Axis Origin Y"))
        db.setValue(self._xpath + '/rotationAxisOrigin/z', self._ui.rotationAxisOriginZ.text(),
                    self.tr("Rotating-Axis Origin Z"))
        db.setValue(self._xpath + '/rotationAxisDirection/x', self._ui.rotationAxisDirectionX.text(),
                    self.tr("Rotating-Axis Direction X"))
        db.setValue(self._xpath + '/rotationAxisDirection/y', self._ui.rotationAxisDirectionY.text(),
                    self.tr("Rotating-Axis Direction Y"))
        db.setValue(self._xpath + '/rotationAxisDirection/z', self._ui.rotationAxisDirectionZ.text(),
                    self.tr("Rotating-Axis Direction Z"))

        return True
