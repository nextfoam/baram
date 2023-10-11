#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.view.widgets.selector_dialog import SelectorDialog
from baramFlow.view.widgets.enum_combo_box import EnumComboBox
from .interface_dialog_ui import Ui_InterfaceDialog
from .coupled_boundary_condition_dialog import CoupledBoundaryConditionDialog


class InterfaceDialog(CoupledBoundaryConditionDialog):
    BOUNDARY_TYPE = BoundaryType.INTERFACE
    RELATIVE_XPATH = '/interface'

    def __init__(self, parent, bcid):
        super().__init__(parent, bcid)
        self._ui = Ui_InterfaceDialog()
        self._ui.setupUi(self)

        self._modeCombo = EnumComboBox(self._ui.mode)

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._coupledBoundary = None
        self._dialog = None

        self._setupModeCombo()

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
        self._modeCombo.currentValueChanged.connect(self._modeChanged)
        self._ui.select.clicked.connect(self._selectCoupledBoundary)

    def _modeChanged(self):
        self._ui.rotationalPeriodic.setVisible(self._modeCombo.isSelected(InterfaceMode.ROTATIONAL_PERIODIC))
        self._ui.translationalPeriodic.setVisible(self._modeCombo.isSelected(InterfaceMode.TRANSLATIONAL_PERIODIC))

    def _load(self):
        path = self._xpath + self.RELATIVE_XPATH

        self._modeCombo.setCurrentValue(self._db.getValue(path + '/mode'))
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
        self._modeCombo.addItem(InterfaceMode.INTERNAL_INTERFACE, self.tr('Internal Interface'))
        self._modeCombo.addItem(InterfaceMode.ROTATIONAL_PERIODIC, self.tr('Rotational Periodic'))
        self._modeCombo.addItem(InterfaceMode.TRANSLATIONAL_PERIODIC, self.tr('Translational Periodic'))
        if not GeneralDB.isCompressible() and not ModelsDB.isMultiphaseModelOn() and ModelsDB.isSpeciesModelOn()\
                and len(self._db.getRegions()) > 1:
            self._modeCombo.addItem(InterfaceMode.REGION_INTERFACE, self.tr('Region Interface'))

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
        mode = self._modeCombo.currentValue()
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
