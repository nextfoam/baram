#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from view.widgets.selector_dialog import SelectorDialog
from .interface_dialog_ui import Ui_InterfaceDialog
from .coupled_boundary_condition_dialog import CoupledBoundaryConditionDialog


class InterfaceDialog(CoupledBoundaryConditionDialog):
    BOUNDARY_TYPE = BoundaryType.INTERFACE
    RELATIVE_XPATH = '/interface'

    def __init__(self, parent, bcid):
        super().__init__(parent, bcid)
        self._ui = Ui_InterfaceDialog()
        self._ui.setupUi(self)

        self._modes = {
            InterfaceMode.INTERNAL_INTERFACE.value: self.tr('Internal Interface'),
            InterfaceMode.ROTATIONAL_PERIODIC.value: self.tr('Rotational Periodic'),
            InterfaceMode.TRANSLATIONAL_PERIODIC.value: self.tr('Translational Periodic'),
            InterfaceMode.REGION_INTERFACE.value: self.tr('Region Interface'),
        }
        self._setupModeCombo()

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._coupledBoundary = None
        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        if not self._coupledBoundary:
            QMessageBox.critical(self, self.tr('Input Error'), self.tr('Select Coupled Boundary'))
            return

        writer = CoreDBWriter()
        coupleTypeChanged = self._changeCoupledBoundary(writer, self._coupledBoundary, self.BOUNDARY_TYPE)
        self._writeConditions(writer, self._xpath + self.RELATIVE_XPATH)
        self._writeConditions(writer, BoundaryDB.getXPath(self._coupledBoundary) + self.RELATIVE_XPATH, True)

        errorCount = writer.write()
        if errorCount == 0:
            if coupleTypeChanged:
                self.boundaryTypeChanged.emit(int(self._coupledBoundary))

            super().accept()
        else:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())

    def _connectSignalsSlots(self):
        self._ui.mode.currentIndexChanged.connect(self._modeChanged)
        self._ui.select.clicked.connect(self._selectCoupledBoundary)

    def _modeChanged(self):
        mode = self._ui.mode.currentData()
        self._ui.rotationalPeriodic.setVisible(mode == InterfaceMode.ROTATIONAL_PERIODIC.value)
        self._ui.translationalPeriodic.setVisible(mode == InterfaceMode.TRANSLATIONAL_PERIODIC.value)

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.mode.setCurrentText(self._modes[self._db.getValue(path + '/mode')])
        self._setCoupledBoundary(self._db.getValue(self._xpath + '/coupledBoundary'))
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
        if not self._dialog:
            self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                          BoundaryDB.getCyclicAMIBoundarySelectorItems(self, self._bcid))
            self._dialog.accepted.connect(self._coupledBoundaryAccepted)

        self._dialog.open()

    def _coupledBoundaryAccepted(self):
        self._setCoupledBoundary(str(self._dialog.selectedItem()))

    def _setCoupledBoundary(self, bcid):
        if bcid != '0':
            self._coupledBoundary = str(bcid)
            self._ui.coupledBoundary.setText(BoundaryDB.getBoundaryText(bcid))
        else:
            self._coupledBoundary = 0
            self._ui.coupledBoundary.setText('')

    def _writeConditions(self, writer, xpath, couple=False):
        mode = self._ui.mode.currentData()
        writer.append(xpath + '/mode', mode, None)

        if mode == InterfaceMode.ROTATIONAL_PERIODIC.value:
            writer.append(xpath + '/rotationAxisOrigin/x',
                          self._ui.rotationAxisX.text(), self.tr('Rotation Axis Origin X'))
            writer.append(xpath + '/rotationAxisOrigin/y',
                          self._ui.rotationAxisY.text(), self.tr('Rotation Axis Origin Y'))
            writer.append(xpath + '/rotationAxisOrigin/z',
                          self._ui.rotationAxisZ.text(), self.tr('Rotation Axis Origin Z'))
            writer.append(xpath + '/rotationAxisDirection/x',
                          self._ui.rotationDirectionX.text(), self.tr('Rotation Axis Direction X'))
            writer.append(xpath + '/rotationAxisDirection/y',
                          self._ui.rotationDirectionY.text(), self.tr('Rotation Axis Direction Y'))
            writer.append(xpath + '/rotationAxisDirection/z',
                          self._ui.rotationDirectionZ.text(), self.tr('Rotation Axis Direction Z'))
        elif mode == InterfaceMode.TRANSLATIONAL_PERIODIC.value:
            if couple:
                writer.append(xpath + '/translationVector/x', str(-int(self._ui.translationVectorX.text())), None)
                writer.append(xpath + '/translationVector/y', str(-int(self._ui.translationVectorY.text())), None)
                writer.append(xpath + '/translationVector/z', str(-int(self._ui.translationVectorZ.text())), None)
            else:
                writer.append(xpath + '/translationVector/x',
                              self._ui.translationVectorX.text(), self.tr('Translation Vector X'))
                writer.append(xpath + '/translationVector/y',
                              self._ui.translationVectorY.text(), self.tr('Translation Vector Y'))
                writer.append(xpath + '/translationVector/z',
                              self._ui.translationVectorZ.text(), self.tr('Translation Vector Z'))
