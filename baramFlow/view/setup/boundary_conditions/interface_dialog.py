#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from .interface_dialog_ui import Ui_InterfaceDialog
from .coupled_boundary_condition_dialog import CoupledBoundaryConditionDialog


class InterfaceDialog(CoupledBoundaryConditionDialog):
    BOUNDARY_TYPE = BoundaryType.INTERFACE
    RELATIVE_XPATH = '/interface'

    def __init__(self, parent, bcid):
        super().__init__(parent, bcid)
        self._ui = Ui_InterfaceDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)
        self._region = BoundaryDB.getBoundaryRegion(bcid)
        self._coupledBoundary = None
        self._dialog = None

        self._setupModeCombo()

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        if not self._ui.coupledBoundary.text():
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
        self._ui.mode.currentDataChanged.connect(self._modeChanged)
        self._ui.select.clicked.connect(self._selectCoupledBoundary)

    def _modeChanged(self, mode):
        self._ui.rotationalPeriodic.setVisible(mode == InterfaceMode.ROTATIONAL_PERIODIC)
        self._ui.translationalPeriodic.setVisible(mode == InterfaceMode.TRANSLATIONAL_PERIODIC)
        self._dialog = None

        if (self._coupledBoundary
                and (mode == InterfaceMode.REGION_INTERFACE
                     or BoundaryDB.getBoundaryRegion(self._coupledBoundary) == self._region)):
            self._ui.coupledBoundary.setText(BoundaryDB.getBoundaryText(self._coupledBoundary))
        else:
            self._ui.coupledBoundary.setText('')

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.mode.setCurrentData(InterfaceMode(db.getValue(path + '/mode')))
        self._setCoupledBoundary(db.getValue(self._xpath + '/coupledBoundary'))
        self._ui.rotationAxisX.setText(db.getValue(path + '/rotationAxisOrigin/x'))
        self._ui.rotationAxisY.setText(db.getValue(path + '/rotationAxisOrigin/y'))
        self._ui.rotationAxisZ.setText(db.getValue(path + '/rotationAxisOrigin/z'))
        self._ui.rotationDirectionX.setText(db.getValue(path + '/rotationAxisDirection/x'))
        self._ui.rotationDirectionY.setText(db.getValue(path + '/rotationAxisDirection/y'))
        self._ui.rotationDirectionZ.setText(db.getValue(path + '/rotationAxisDirection/z'))
        self._ui.translationVectorX.setText(db.getValue(path + '/translationVector/x'))
        self._ui.translationVectorY.setText(db.getValue(path + '/translationVector/y'))
        self._ui.translationVectorZ.setText(db.getValue(path + '/translationVector/z'))

    def _setupModeCombo(self):
        db = coredb.CoreDB()
        self._ui.mode.addEnumItems({
            InterfaceMode.INTERNAL_INTERFACE: self.tr('Internal Interface'),
            InterfaceMode.ROTATIONAL_PERIODIC: self.tr('Rotational Periodic'),
            InterfaceMode.TRANSLATIONAL_PERIODIC: self.tr('Translational Periodic')
        })

        if (not GeneralDB.isCompressible() and not ModelsDB.isMultiphaseModelOn() and ModelsDB.isSpeciesModelOn()
                and len(db.getRegions()) > 1):
            self._ui.mode.addEnumItem(InterfaceMode.REGION_INTERFACE, self.tr('Region Interface'))

    def _selectCoupledBoundary(self):
        if not self._dialog:
            self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                          BoundaryDB.getBoundarySelectorItemsForCoupling(
                                              self._bcid,
                                              self._ui.mode.currentData() != InterfaceMode.REGION_INTERFACE))
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
        writer.append(xpath + '/mode', mode.value, None)

        if mode == InterfaceMode.ROTATIONAL_PERIODIC:
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
        elif mode == InterfaceMode.TRANSLATIONAL_PERIODIC:
            if couple:
                writer.append(xpath + '/translationVector/x', str(-float(self._ui.translationVectorX.text())), None)
                writer.append(xpath + '/translationVector/y', str(-float(self._ui.translationVectorY.text())), None)
                writer.append(xpath + '/translationVector/z', str(-float(self._ui.translationVectorZ.text())), None)
            else:
                writer.append(xpath + '/translationVector/x',
                              self._ui.translationVectorX.text(), self.tr('Translation Vector X'))
                writer.append(xpath + '/translationVector/y',
                              self._ui.translationVectorY.text(), self.tr('Translation Vector Y'))
                writer.append(xpath + '/translationVector/z',
                              self._ui.translationVectorZ.text(), self.tr('Translation Vector Z'))
