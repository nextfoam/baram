#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy
from enum import Enum, auto

import qasync
from PySide6.QtCore import QCoreApplication, Signal
from PySide6.QtGui import QRegularExpressionValidator

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import ScalarSpecificationMethod, UserDefinedScalar
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .user_defined_scalar_dialog_ui import Ui_UserDefinedScalarDialog


RESERVED_FIELDS = [
    'alphat', 'epsilon', 'k', 'nut', 'nuTilda', 'omega',
    'p', 'p_rgh',
    'T',
    'U', 'Ux', 'Uy', 'Uz',
    'rho'
]


ALL_MATERIALS_TEXT = QCoreApplication.translate('UserDefinedScalar', 'All')
ALL_MATERIALS_MID = '0'

SCALAR_SPECIFICATION_METHODS = {
    ScalarSpecificationMethod.CONSTANT:
        QCoreApplication.translate('UserDefinedScalar', 'Constant'),
    # ScalarSpecificationMethod.TURBULENT_VISCOSITY:              QCoreApplication.translate('UserDefinedScalar', 'Turbulent Viscosity'),
    ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY:
        QCoreApplication.translate('UserDefinedScalar', 'Laminar and Turbulent Viscosity')
}


class Mode(Enum):
    Add = auto()
    Edit = auto()


class UserDefinedScalarDialog(ResizableDialog):
    dataAccepted = Signal(UserDefinedScalar)

    def __init__(self, parent, scalar: UserDefinedScalar):
        super().__init__(parent)
        self._ui = Ui_UserDefinedScalarDialog()
        self._ui.setupUi(self)

        self._scalar = scalar
        self._target = None
        self._mode = Mode.Add

        db = coredb.CoreDB()
        if ModelsDB.isMultiphaseModelOn():
            self._ui.targetLabel.setText(self.tr('Material'))
            self._ui.target.addItem(ALL_MATERIALS_TEXT, ALL_MATERIALS_MID)
            for mid, name, _, _ in MaterialDB.getMaterials():
                self._ui.target.addItem(name, mid)
        elif RegionDB.isMultiRegion():
            for rname in db.getRegions():
                self._ui.target.addItem(rname)
        else:
            self._ui.basicsLayout.setRowVisible(self._ui.target, False)

        self._ui.specificationMethod.addItem(self.tr('Constant'),
                                             ScalarSpecificationMethod.CONSTANT)
        self._ui.specificationMethod.addItem(self.tr('Laminar and Turbulent Viscosity'),
                                             ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY)

        if scalar.fieldName:
            self._ui.fieldName.setEnabled(False)
            self._ui.fieldName.setText(scalar.fieldName)
            self._mode = Mode.Edit
        else:
            self._ui.fieldName.setValidator(QRegularExpressionValidator('^[A-Za-z][A-Za-z0-9]*'))

        self._connectSignalsSlots()
        self._load(scalar)

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._onSpecificationMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self, scalar: UserDefinedScalar):
        if ModelsDB.isMultiphaseModelOn():
            if scalar.material != '0':
                self._ui.target.setCurrentText(MaterialDB.getName(scalar.material))
            else:
                self._ui.target.setCurrentIndex(0)
        elif RegionDB.isMultiRegion() and scalar.rname:
            self._ui.target.setCurrentText(scalar.rname)

        self._ui.fieldName.setText(scalar.fieldName)
        self._ui.specificationMethod.setCurrentIndex(self._ui.specificationMethod.findData(scalar.specificationMethod))
        self._ui.diffusivity.setPFloat(scalar.constantDiffusivity)
        self._ui.laminarViscosityCoefficient.setPFloat(scalar.laminarViscosityCoefficient)
        self._ui.turbulentViscosityCoefficient.setPFloat(scalar.turbulentViscosityCoefficient)

        self._onSpecificationMethodChanged()

    def _onSpecificationMethodChanged(self):
        method = self._ui.specificationMethod.currentData()
        self._ui.constant.setVisible(method == ScalarSpecificationMethod.CONSTANT)
        self._ui.laminarAndTurbulentViscosity.setVisible(
            method == ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY)

    @qasync.asyncSlot()
    async def _accept(self):
        fieldName = self._ui.fieldName.text().strip()

        if fieldName == '':
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Field Name is required.'))
            return

        if fieldName in RESERVED_FIELDS:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Field Name is not available.'))
            return

        if self._mode == Mode.Add and self.parent().fieldNameExists(fieldName):
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Field Name already exists.'))
            return

        data = deepcopy(self._scalar)
        data.fieldName = self._ui.fieldName.text().strip()
        try:
            if ModelsDB.isMultiphaseModelOn():
                data.material = self._ui.target.currentData()
            elif RegionDB.isMultiRegion():
                data.rname = self._ui.target.currentText()

            data.specificationMethod = self._ui.specificationMethod.currentData()
            if data.specificationMethod == ScalarSpecificationMethod.CONSTANT:
                data.constantDiffusivity = self._ui.diffusivity.pFloat(self.tr('Diffusivity'))
            else:
                data.laminarViscosityCoefficient = self._ui.laminarViscosityCoefficient.pFloat(
                    self.tr('Laminar Viscosity Coefficient'))
                data.turbulentViscosityCoefficient = self._ui.turbulentViscosityCoefficient.pFloat(
                    self.tr('Turbulent Viscosity Coefficient'))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.dataAccepted.emit(data)
        self.accept()
