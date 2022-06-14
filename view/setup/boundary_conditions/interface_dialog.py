#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.resizable_dialog import ResizableDialog
from view.widgets.selector_dialog import SelectorDialog
from .interface_dialog_ui import Ui_InterfaceDialog
from .boundary_db import BoundaryDB, InterfaceMode


class InterfaceDialog(ResizableDialog):
    RELATIVE_PATH = '/interface'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_InterfaceDialog()
        self._ui.setupUi(self)

        self._modes = {
            InterfaceMode.INTERNAL_INTERFACE.value: self.tr("Internal Interface"),
            InterfaceMode.ROTATIONAL_PERIODIC.value: self.tr("Rotational Periodic"),
            InterfaceMode.TRANSLATIONAL_PERIODIC.value: self.tr("Translational Periodic"),
            InterfaceMode.REGION_INTERFACE.value: self.tr("Region Interface"),
        }
        self._setupModeCombo()

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getBoundaryXPath(bcid)
        self._bcid = bcid
        self._coupledBoundary = None
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.mode.currentIndexChanged.connect(self._modeChanged)
        self._ui.select.clicked.connect(self._selectCoupledBoundary)

    def _modeChanged(self):
        mode = self._ui.mode.currentData()
        self._ui.rotationalPeriodic.setVisible(mode == InterfaceMode.ROTATIONAL_PERIODIC.value)
        self._ui.translationalPeriodic.setVisible(mode == InterfaceMode.TRANSLATIONAL_PERIODIC.value)

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        mode = self._ui.mode.currentData()
        writer.append(path + '/mode', mode, None)

        if self._coupledBoundary is None:
            QMessageBox.critical(self, self.tr("Input Error"), "Select Coupled Boundary")
            return
        else:
            writer.append(path + '/coupledBoundary', self._coupledBoundary, self.tr("Coupled Boundary"))

        if mode == InterfaceMode.ROTATIONAL_PERIODIC.value:
            writer.append(path + '/rotationAxisOrigin/x',
                          self._ui.rotationAxisX.text(), self.tr("Rotation Axis Origin X"))
            writer.append(path + '/rotationAxisOrigin/y',
                          self._ui.rotationAxisY.text(), self.tr("Rotation Axis Origin Y"))
            writer.append(path + '/rotationAxisOrigin/z',
                          self._ui.rotationAxisZ.text(), self.tr("Rotation Axis Origin Z"))
            writer.append(path + '/rotationAxisDirection/x',
                          self._ui.rotationDirectionX.text(), self.tr("Rotation Axis Direction X"))
            writer.append(path + '/rotationAxisDirection/y',
                          self._ui.rotationDirectionY.text(), self.tr("Rotation Axis Direction Y"))
            writer.append(path + '/rotationAxisDirection/z',
                          self._ui.rotationDirectionZ.text(), self.tr("Rotation Axis Direction Z"))
        elif mode == InterfaceMode.TRANSLATIONAL_PERIODIC.value:
            writer.append(path + '/translationVector/x',
                          self._ui.translationVectorX.text(), self.tr("Translation Vector X"))
            writer.append(path + '/translationVector/y',
                          self._ui.translationVectorY.text(), self.tr("Translation Vector Y"))
            writer.append(path + '/translationVector/z',
                          self._ui.translationVectorZ.text(), self.tr("Translation Vector Z"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        self._ui.mode.setCurrentText(self._modes[self._db.getValue(path + '/mode')])
        bcid = self._db.getValue(path + '/coupledBoundary')
        if bcid:
            self._setCoupledBoundary(bcid)
        self._ui.rotationAxisX.setText(self._db.getValue(path + '/rotationAxisOrigin/x'))
        self._ui.rotationAxisY.setText(self._db.getValue(path + '/rotationAxisOrigin/y'))
        self._ui.rotationAxisZ.setText(self._db.getValue(path + '/rotationAxisOrigin/z'))
        self._ui.rotationDirectionX.setText(self._db.getValue(path + '/rotationAxisDirection/x'))
        self._ui.rotationDirectionY.setText(self._db.getValue(path + '/rotationAxisDirection/y'))
        self._ui.rotationDirectionZ.setText(self._db.getValue(path + '/rotationAxisDirection/z'))
        self._ui.translationVectorX.setText(self._db.getValue(path + '/translationVector/x'))
        self._ui.translationVectorY.setText(self._db.getValue(path + '/translationVector/y'))
        self._ui.translationVectorZ.setText(self._db.getValue(path + '/translationVector/z'))
        self._modeChanged()

    def _setupModeCombo(self):
        for value, text in self._modes.items():
            self._ui.mode.addItem(text, value)

    def _selectCoupledBoundary(self):
        if self._dialog is None:
            self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                          BoundaryDB.getCyclicAMIBoundaries(self._bcid))
            self._dialog.accepted.connect(self._coupledBoundaryAccepted)

        self._dialog.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(str(self._dialog.selectedItem()))

    def _setCoupledBoundary(self, bcid):
        self._coupledBoundary = bcid
        self._ui.coupledBoundary.setText(f'{BoundaryDB.getBoundaryName(bcid)} / {BoundaryDB.getBoundaryRegion(bcid)}')
