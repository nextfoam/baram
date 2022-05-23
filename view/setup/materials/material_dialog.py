#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from PySide6.QtCore import Qt

from view.widgets.resizable_dialog import ResizableDialog, ResizableForm
from view.widgets.polynomial_dialog import PolynomialDialog
from .material import Material
from .material_dialog_ui import Ui_MaterialDialog


class MaterialDialog(ResizableDialog):
    class PROPERTY_TYPE(Enum):
        CONSTANT = auto()
        PERFECT_GAS = auto()
        SUTHERLAND = auto()
        POLYNOMIAL = auto()

    class PROPERTY_FORM_ROW(Enum):
        MOLECULAR_WEIGHT = 0
        ABSORPTION_COEFFICIENT = auto()
        SURFACE_TENSION = auto()
        SATURATION_PRESSURE = auto()
        EMISSIVITY = auto()


    def __init__(self, material):
        super().__init__()
        self._ui = Ui_MaterialDialog()
        self._ui.setupUi(self)

        self._setup(material)
        self._connectSignalsSlots()

    def _setup(self, material):
        self._ui.material.setText(material.name + " (" + material.phase.name + ")")
        self._setupPhase(material.phase)
        self._setupPropertyTypes(material.phase)
        self._resizeDialog(self)

    def _setupPhase(self, phase):
        self._propertyLayout = ResizableForm(self._ui.properties.layout())

        self._fluidGroup = [
            self.PROPERTY_FORM_ROW.MOLECULAR_WEIGHT.value,
        ]

        self._gasGroup = [
            self.PROPERTY_FORM_ROW.ABSORPTION_COEFFICIENT.value,
        ]

        self._liquidGroup = [
            self.PROPERTY_FORM_ROW.SURFACE_TENSION.value,
            self.PROPERTY_FORM_ROW.SATURATION_PRESSURE.value,
        ]

        self._solidGroup = [
            self.PROPERTY_FORM_ROW.EMISSIVITY.value,
        ]

        self._ui.viscosityGroup.setVisible(phase != Material.PHASE.Solid)
        self._propertyLayout.setRowsVisible(self._fluidGroup, phase != Material.PHASE.Solid)
        self._propertyLayout.setRowsVisible(self._gasGroup, phase == Material.PHASE.Gas)
        self._propertyLayout.setRowsVisible(self._liquidGroup, phase == Material.PHASE.Liquid)
        self._propertyLayout.setRowsVisible(self._solidGroup, phase == Material.PHASE.Solid)

        self._ui.densityEdit.setEnabled(False)
        self._ui.specificHeatEdit.setEnabled(False)
        self._ui.viscosityEdit.setEnabled(False)
        self._ui.thermalConductivityEdit.setEnabled(False)

    def _setupPropertyTypes(self, phase):
        self._propertyTypes = {
            self.PROPERTY_TYPE.CONSTANT: self.tr("constant"),
            self.PROPERTY_TYPE.PERFECT_GAS: self.tr("perfect gas"),
            self.PROPERTY_TYPE.SUTHERLAND: self.tr("sutherland"),
            self.PROPERTY_TYPE.POLYNOMIAL: self.tr("polynomial")
        }

        self._setupPropertyTypeCombo(
            self._ui.densityType, [
                self.PROPERTY_TYPE.CONSTANT,
                self.PROPERTY_TYPE.PERFECT_GAS
            ]
        )

        self._setupPropertyTypeCombo(
            self._ui.specificHeatType, [
                self.PROPERTY_TYPE.CONSTANT,
                self.PROPERTY_TYPE.POLYNOMIAL
            ]
        )

        if phase == Material.PHASE.Gas:
            self._setupPropertyTypeCombo(
                self._ui.viscosityType, [
                    self.PROPERTY_TYPE.CONSTANT,
                    self.PROPERTY_TYPE.SUTHERLAND,
                    self.PROPERTY_TYPE.POLYNOMIAL
                ]
            )
        elif phase == Material.PHASE.Liquid:
            self._setupPropertyTypeCombo(
                self._ui.viscosityType, [
                    self.PROPERTY_TYPE.CONSTANT,
                    self.PROPERTY_TYPE.POLYNOMIAL
                ]
            )

        self._setupPropertyTypeCombo(
            self._ui.thermalConductivityType, [
                self.PROPERTY_TYPE.CONSTANT,
                self.PROPERTY_TYPE.POLYNOMIAL
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
        self._ui.densityEdit.setEnabled(type_ == self.PROPERTY_TYPE.PERFECT_GAS)
        self._ui.constantDensity.setEnabled(type_ == self.PROPERTY_TYPE.CONSTANT)

    def _specificHeatTypeChanged(self, index):
        type_ = self._ui.specificHeatType.itemData(index, Qt.UserRole)
        self._ui.specificHeatEdit.setEnabled(type_ == self.PROPERTY_TYPE.POLYNOMIAL)
        self._ui.constantSpecificHeat.setEnabled(type_ == self.PROPERTY_TYPE.CONSTANT)

    def _viscosityTypeChanged(self, index):
        type_ = self._ui.viscosityType.itemData(index, Qt.UserRole)
        self._ui.viscosityEdit.setEnabled(type_ == self.PROPERTY_TYPE.POLYNOMIAL)
        self._ui.constantViscosity.setEnabled(type_ == self.PROPERTY_TYPE.CONSTANT)
        self._ui.sutherlandCoefficient.setEnabled(type_ == self.PROPERTY_TYPE.SUTHERLAND)
        self._ui.sutherlandTemperature.setEnabled(type_ == self.PROPERTY_TYPE.SUTHERLAND)

    def _thermalConductivityTypeChanged(self, index):
        type_ = self._ui.thermalConductivityType.itemData(index, Qt.UserRole)
        self._ui.thermalConductivityEdit.setEnabled(type_ == self.PROPERTY_TYPE.POLYNOMIAL)
        self._ui.constantThermalConductivity.setEnabled(type_ == self.PROPERTY_TYPE.CONSTANT)

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