#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

import qasync
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QRegularExpressionValidator

from widgets.async_message_box import AsyncMessageBox
from widgets.validation.validation import FormValidator

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
    ScalarSpecificationMethod.CONSTANT:                         QCoreApplication.translate('UserDefinedScalar', 'Constant'),
    # ScalarSpecificationMethod.TURBULENT_VISCOSITY:              QCoreApplication.translate('UserDefinedScalar', 'Turbulent Viscosity'),
    ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY:  QCoreApplication.translate('UserDefinedScalar', 'Laminar and Turbulent Viscosity')
}


class Mode(Enum):
    Add = auto()
    Edit = auto()


class UserDefiendScalarDialog(ResizableDialog):
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

        self._ui.specificationMethod.addEnumItems(SCALAR_SPECIFICATION_METHODS)

        if scalar.fieldName:
            self._ui.fieldName.setEnabled(False)
            self._ui.fieldName.setText(scalar.fieldName)
            self._mode = Mode.Edit
        else:
            self._ui.fieldName.setValidator(QRegularExpressionValidator('^[A-Za-z][A-Za-z0-9]*'))

        self._connectSignalsSlots()
        self._load(scalar)

    def scalar(self) -> UserDefinedScalar:
        self._scalar.fieldName = self._ui.fieldName.text()

        if ModelsDB.isMultiphaseModelOn():
            self._scalar.material = self._ui.target.currentData()
        elif RegionDB.isMultiRegion():
            self._scalar.rname = self._ui.target.currentText()

        self._scalar.specificationMethod = self._ui.specificationMethod.currentData()
        if self._scalar.specificationMethod == ScalarSpecificationMethod.CONSTANT:
            self._scalar.constantDiffusivity = self._ui.diffusivity.text()
        else:
            self._scalar.laminarViscosityCoefficient = self._ui.laminarViscosityCoefficient.text()
            self._scalar.turbulentViscosityCoefficient = self._ui.turbulentViscosityCoefficient.text()

        return self._scalar

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self, scalar):
        if ModelsDB.isMultiphaseModelOn():
            if scalar.material != '0':
                self._ui.target.setCurrentText(MaterialDB.getName(scalar.material))
            else:
                self._ui.target.setCurrentIndex(0)
        elif RegionDB.isMultiRegion() and scalar.rname:
            self._ui.target.setCurrentText(scalar.rname)

        self._ui.fieldName.setText(scalar.fieldName)
        self._ui.specificationMethod.setCurrentData(scalar.specificationMethod)
        self._ui.diffusivity.setText(scalar.constantDiffusivity)
        self._ui.laminarViscosityCoefficient.setText(scalar.laminarViscosityCoefficient)
        self._ui.turbulentViscosityCoefficient.setText(scalar.turbulentViscosityCoefficient)

    def _specificationMethodChanged(self, method):
        self._ui.constant.setVisible(method == ScalarSpecificationMethod.CONSTANT)
        self._ui.laminarAndTurbulentViscosity.setVisible(
            method == ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY)

    @qasync.asyncSlot()
    async def _accept(self):
        fieldName = self._ui.fieldName.text()

        if fieldName in RESERVED_FIELDS:
            await AsyncMessageBox().information(self, 'Input Error', 'Field Name is not available.')
            return

        if self._mode == Mode.Add and self.parent().fieldNameExists(fieldName):
            await AsyncMessageBox().information(self, 'Input Error', 'Field Name already exists.')
            return

        validator = FormValidator()
        validator.addRequiredValidation(self._ui.fieldName, self.tr('Field Name'))
        validator.addRequiredValidation(self._ui.diffusivity, self.tr('Diffusivity'))
        validator.addRequiredValidation(self._ui.laminarViscosityCoefficient, self.tr('Laminar Viscosity Coefficient'))
        validator.addRequiredValidation(self._ui.turbulentViscosityCoefficient,
                                        self.tr('Turbulent Viscosity Coefficient'))

        valid, msg = validator.validate()
        if not valid:
            await AsyncMessageBox().information(self, self.tr('Input Error'), msg)
            return

        self.accept()
