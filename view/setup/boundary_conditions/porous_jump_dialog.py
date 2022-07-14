#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB
from .porous_jump_dialog_ui import Ui_PorousJumpDialog


class PorousJumpDialog(QDialog):
    RELATIVE_XPATH = '/porousJump'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_PorousJumpDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)

        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        writer.append(path + '/darcyCoefficient', self._ui.darcyCoefficient.text(), self.tr("Darcy Coefficient"))
        writer.append(path + '/inertialCoefficient',
                      self._ui.inertialCoefficient.text(), self.tr("Inertial Coefficient"))
        writer.append(path + '/porousMediaThickness',
                      self._ui.porousMedieThickness.text(), self.tr("Porous Media Thickness"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.darcyCoefficient.setText(self._db.getValue(path + '/darcyCoefficient'))
        self._ui.inertialCoefficient.setText(self._db.getValue(path + '/inertialCoefficient'))
        self._ui.porousMedieThickness.setText(self._db.getValue(path + '/porousMediaThickness'))
