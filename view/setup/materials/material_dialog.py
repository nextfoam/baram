#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, Flag, auto

from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFormLayout

from view.widgets.number_input_dialog import PolynomialDialog
from .material import Phase
from .material_dialog_ui import Ui_MaterialDialog


class PropertyType(Flag):
    CONSTANT = auto()
    PERFECT_GAS = auto()
    SUTHERLAND = auto()
    POLYNOMIAL = auto()


class PropertyFormRow(Enum):
    MOLECULAR_WEIGHT = 0
    ABSORPTION_COEFFICIENT = auto()
    SURFACE_TENSION = auto()
    SATURATION_PRESSURE = auto()
    EMISSIVITY = auto()


class MaterialDialog(QDialog):
    def __init__(self, material):
        super().__init__()
        self._ui = Ui_MaterialDialog()
        self._ui.setupUi(self)

        self._propertyTypes = {
            PropertyType.CONSTANT: self.tr("constant"),
            PropertyType.PERFECT_GAS: self.tr("perfect gas"),
            PropertyType.SUTHERLAND: self.tr("sutherland"),
            PropertyType.POLYNOMIAL: self.tr("polynomial")
        }

        self._propertyFormRows = {
            PropertyFormRow.MOLECULAR_WEIGHT.value: Phase.FLUID,
            PropertyFormRow.ABSORPTION_COEFFICIENT.value: Phase.GAS,
            PropertyFormRow.SURFACE_TENSION.value: Phase.LIQUID,
            PropertyFormRow.SATURATION_PRESSURE.value: Phase.LIQUID,
            PropertyFormRow.EMISSIVITY.value: Phase.SOLID,
        }

        self._setMaterial(material)
        self._connectSignalsSlots()

        self._ui.densityEdit.setEnabled(False)
        self._ui.specificHeatEdit.setEnabled(False)
        self._ui.viscosityEdit.setEnabled(False)
        self._ui.thermalConductivityEdit.setEnabled(False)

    def _showPropertyRows(self, phase):
        form = self._ui.properties.layout()
        rows = []
        for i in range(form.rowCount()):
            labelItem = form.itemAt(0, QFormLayout.LabelRole)
            fieldItem = form.itemAt(0, QFormLayout.FieldRole)
            label = labelItem.widget()
            field = fieldItem.widget()
            rows.append([label, field])
            form.removeItem(labelItem)
            form.removeItem(fieldItem)
            form.removeRow(0)
            label.setParent(None)
            field.setParent(None)

        for i, p in self._propertyFormRows.items():
            if p & phase:
                form.addRow(rows[i][0], rows[i][1])

    def _setMaterial(self, material):
        self._ui.material.setText(material.name + " (" + material.phase.name + ")")
        self._ui.viscosityGroup.setVisible(material.phase != Phase.SOLID)
        self._showPropertyRows(material.phase)
        self._setupPropertyTypes(material.phase)

        QTimer.singleShot(0, lambda: self.adjustSize())

    def _setupPropertyTypes(self, phase):
        self._setupPropertyTypeCombo(
            self._ui.densityType, [
                PropertyType.CONSTANT,
                PropertyType.PERFECT_GAS
            ]
        )

        self._setupPropertyTypeCombo(
            self._ui.specificHeatType, [
                PropertyType.CONSTANT,
                PropertyType.POLYNOMIAL
            ]
        )

        if phase == Phase.GAS:
            self._setupPropertyTypeCombo(
                self._ui.viscosityType, [
                    PropertyType.CONSTANT,
                    PropertyType.SUTHERLAND,
                    PropertyType.POLYNOMIAL
                ]
            )
        elif phase == Phase.LIQUID:
            self._setupPropertyTypeCombo(
                self._ui.viscosityType, [
                    PropertyType.CONSTANT,
                    PropertyType.POLYNOMIAL
                ]
            )

        self._setupPropertyTypeCombo(
            self._ui.thermalConductivityType, [
                PropertyType.CONSTANT,
                PropertyType.POLYNOMIAL
            ]

        )

    def _setupPropertyTypeCombo(self, combo, types):
        for type_ in types:
            combo.addItem(self._propertyTypes[type_], type_)

    def _connectSignalsSlots(self):
        self._ui.densityType.currentIndexChanged.connect(self._densityTypeChanged)
        self._ui.specificHeatType.currentIndexChanged.connect(self._specificHeatTypeChanged)
        self._ui.viscosityType.currentIndexChanged.connect(self._viscosityTypeChanged)
        self._ui.thermalConductivityType.currentIndexChanged.connect(self._thermalConductivityTypeChanged)
        self._ui.densityEdit.clicked.connect(self._editDensity)
        self._ui.specificHeatEdit.clicked.connect(self._editSpecificHeat)
        self._ui.viscosityEdit.clicked.connect(self._editViscosity)
        self._ui.thermalConductivityEdit.clicked.connect(self._editThermalConductivity)

    def _densityTypeChanged(self, index):
        type_ = self._ui.densityType.itemData(index, Qt.UserRole)
        self._ui.densityEdit.setEnabled(type_ == PropertyType.PERFECT_GAS)
        self._ui.constantDensity.setEnabled(type_ == PropertyType.CONSTANT)

    def _specificHeatTypeChanged(self, index):
        type_ = self._ui.specificHeatType.itemData(index, Qt.UserRole)
        self._ui.specificHeatEdit.setEnabled(type_ == PropertyType.POLYNOMIAL)
        self._ui.constantSpecificHeat.setEnabled(type_ == PropertyType.CONSTANT)

    def _viscosityTypeChanged(self, index):
        type_ = self._ui.viscosityType.itemData(index, Qt.UserRole)
        self._ui.viscosityEdit.setEnabled(type_ == PropertyType.POLYNOMIAL)
        self._ui.constantViscosity.setEnabled(type_ == PropertyType.CONSTANT)
        self._ui.sutherlandCoefficient.setEnabled(type_ == PropertyType.SUTHERLAND)
        self._ui.sutherlandTemperature.setEnabled(type_ == PropertyType.SUTHERLAND)

    def _thermalConductivityTypeChanged(self, index):
        type_ = self._ui.thermalConductivityType.itemData(index, Qt.UserRole)
        self._ui.thermalConductivityEdit.setEnabled(type_ == PropertyType.POLYNOMIAL)
        self._ui.constantThermalConductivity.setEnabled(type_ == PropertyType.CONSTANT)

    def _editDensity(self):
        pass

    def _editSpecificHeat(self):
        dialog = PolynomialDialog(self.tr("Polynomial Specific Heat"))
        dialog.exec()

    def _editViscosity(self):
        dialog = PolynomialDialog(self.tr("Polynomial Viscosity"))
        dialog.exec()

    def _editThermalConductivity(self):
        dialog = PolynomialDialog(self.tr("Polynomial Thermal Conductivity"))
        dialog.exec()
