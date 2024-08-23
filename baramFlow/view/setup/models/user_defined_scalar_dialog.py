#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QRegularExpressionValidator

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.scalar_model_db import ScalarSpecificationMethod
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

SCALAR_SPECIFICATION_METHODS = {
    ScalarSpecificationMethod.CONSTANT:                         QCoreApplication.translate('UserDefinedScalar', 'Constant'),
    ScalarSpecificationMethod.TURBULENT_VISCOSITY:              QCoreApplication.translate('UserDefinedScalar', 'Turbulent Viscosity'),
    ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY:  QCoreApplication.translate('UserDefinedScalar', 'Laminar and Turbulent Viscosity')
}


class Validator(QObject):
    def __init__(self):
        super().__init__()
        self._message = None

    def message(self):
        return self._message

    def validateFloat(self, edit, label):
        try:
            float(edit.text())
            return edit.text()
        except ValueError:
            self._message = self.tr('Value must be a float - ') + label
            raise

class UserDefiendScalarDialog(ResizableDialog):

    def __init__(self, parent, scalar):
        super().__init__(parent)
        self._ui = Ui_UserDefinedScalarDialog()
        self._ui.setupUi(self)

        self._scalar = scalar
        self._target = None

        db = coredb.CoreDB()
        if ModelsDB.isMultiphaseModelOn():
            self._ui.targetLabel.setText(self.tr('Material'))
            self._ui.target.addItem(ALL_MATERIALS_TEXT, 0)
            for mid, name, _, _ in db.getMaterials():
                self._ui.target.addItem(name, mid)
        elif db.hasMultipleRegions():
            for rname in db.getRegions():
                self._ui.target.addItem(rname)
        else:
            self._ui.basicsLayout.setRowVisible(self._ui.target, False)

        self._ui.specificationMethod.addEnumItems(SCALAR_SPECIFICATION_METHODS)

        if scalar.fieldName:
            self._ui.form.setEnabled(False)
            self._ui.ok.hide()
            self._ui.cancel.setText(self.tr('Close'))
            self._ui.fieldName.setText(scalar.fieldName)
        else:
            self._ui.fieldName.setValidator(QRegularExpressionValidator('^[A-Za-z][A-Za-z0-9]*'))

        self._connectSignalsSlots()
        self._load()

    def scalar(self):
        return self._scalar

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        if ModelsDB.isMultiphaseModelOn():
            if int(self._scalar.material):
                self._ui.target.setCurrentText(MaterialDB.getName(self._scalar.material))
            else:
                self._ui.target.setCurrentIndex(0)
        elif db.hasMultipleRegions() and self._scalar.region:
                self._ui.target.setCurrentText(self._scalar.region)

        self._ui.fieldName.setText(self._scalar.fieldName)
        self._ui.specificationMethod.setCurrentData(self._scalar.specificationMethod)
        self._ui.diffusivity.setText(self._scalar.constantDiffusivity)
        self._ui.laminarViscosityCoefficient.setText(self._scalar.laminarViscosityCoefficient)
        self._ui.turbulentViscosityCoefficient.setText(self._scalar.turbulentViscosityCoefficient)

    def _specificationMethodChanged(self, method):
        self._ui.constant.setVisible(method == ScalarSpecificationMethod.CONSTANT)
        self._ui.laminarAndTurbulentViscosity.setVisible(
            method == ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY)

    @qasync.asyncSlot()
    async def _accept(self):
        fieldName = self._ui.fieldName.text()

        if not fieldName:
            await AsyncMessageBox().information(self, 'Input Error', 'Field Name is required.')
            return

        if fieldName in RESERVED_FIELDS:
            await AsyncMessageBox().information(self, 'Input Error', 'Field Name is not available.')
            return

        if self.parent().fieldNameExists(fieldName):
            await AsyncMessageBox().information(self, 'Input Error', 'Field Name already exists.')
            return

        validator = Validator()
        try:
            db = coredb.CoreDB()
            self._scalar.fieldName = self._ui.fieldName.text()
            self._scalar.specificationMethod = self._ui.specificationMethod.currentData()

            if ModelsDB.isMultiphaseModelOn():
                self._scalar.material = self._ui.target.currentData()
            elif db.hasMultipleRegions():
                self._scalar.region = self._ui.target.currentText()

            if self._scalar.specificationMethod == ScalarSpecificationMethod.CONSTANT:
                self._scalar.constantDiffusivity = validator.validateFloat(self._ui.diffusivity, self.tr('Diffusivity'))
            elif self._scalar.specificationMethod == ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY:
                self._scalar.laminarViscosityCoefficient = validator.validateFloat(self._ui.laminarViscosityCoefficient, self.tr('Laminar Viscosity Coefficient'))
                self._scalar.turbulentViscosityCoefficient = validator.validateFloat(self._ui.turbulentViscosityCoefficient, self.tr('Turbulent Viscosity Coefficient'))
        except ValueError:
            await AsyncMessageBox().information(self, self.tr('Input Error'), validator.message())
            return

        self.accept()
