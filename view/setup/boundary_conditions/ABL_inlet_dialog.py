#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from .ABL_inlet_dialog_ui import Ui_ABLInletDialog
from .boundary_db import BoundaryDB


class ABLInletDialog(QDialog):
    RELATIVE_PATH = '/ablInlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_ABLInletDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        writer.append(path + '/flowDirection/x',
                      self._ui.flowDirectionXComponent.text(), self.tr("Flow Direction X-Component"))
        writer.append(path + '/flowDirection/y',
                      self._ui.flowDirectionYComponent.text(), self.tr("Flow Direction Y-Component"))
        writer.append(path + '/flowDirection/z',
                      self._ui.flowDirectionZComponent.text(), self.tr("Flow Direction Z-Component"))
        writer.append(path + '/groundNormalDirection/x',
                      self._ui.groundNormalDirectionXComponent.text(), self.tr("Ground-Normal Direction X-Component"))
        writer.append(path + '/groundNormalDirection/y',
                      self._ui.groundNormalDirectionYComponent.text(), self.tr("Ground-Normal Direction Y-Component"))
        writer.append(path + '/groundNormalDirection/z',
                      self._ui.groundNormalDirectionZComponent.text(), self.tr("Ground-Normal Direction Z-Component"))
        writer.append(path + '/referenceFlowSpeed',
                      self._ui.referenceFlowSpeed.text(), self.tr("Reference Flow Speed"))
        writer.append(path + '/referenceHeight',
                      self._ui.referenceHeight.text(), self.tr("Reference Height"))
        writer.append(path + '/surfaceRoughnessLength',
                      self._ui.surfaceRoughnessLength.text(), self.tr("Surface Roughness Length"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        self._ui.flowDirectionXComponent.setText(self._db.getValue(path + '/flowDirection/x'))
        self._ui.flowDirectionYComponent.setText(self._db.getValue(path + '/flowDirection/y'))
        self._ui.flowDirectionZComponent.setText(self._db.getValue(path + '/flowDirection/z'))
        self._ui.groundNormalDirectionXComponent.setText(self._db.getValue(path + '/groundNormalDirection/x'))
        self._ui.groundNormalDirectionYComponent.setText(self._db.getValue(path + '/groundNormalDirection/y'))
        self._ui.groundNormalDirectionZComponent.setText(self._db.getValue(path + '/groundNormalDirection/z'))
        self._ui.referenceFlowSpeed.setText(self._db.getValue(path + '/referenceFlowSpeed'))
        self._ui.referenceHeight.setText(self._db.getValue(path + '/referenceHeight'))
        self._ui.surfaceRoughnessLength.setText(self._db.getValue(path + '/surfaceRoughnessLength'))
