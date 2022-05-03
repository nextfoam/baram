#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .material import Material
from .material_dialog_ui import Ui_MaterialDialog
from .polynomial_dialog import PolynomialDialog
from .sutherland_dialog import SutherlandDialog


class MaterialDialog(ResizableDialog):
    def __init__(self, material):
        super().__init__()
        self._ui = Ui_MaterialDialog()
        self._ui.setupUi(self)

        self._fluidGroup = [
            self._ui.visocosityLabel,
            self._ui.viscosityFields,
            self._ui.molecularWeightLabel,
            self._ui.molecularWeight,
        ]

        self._gasGroup = [
            self._ui.absorptionCoefficientLabel,
            self._ui.absorptionCoefficient,
        ]

        self._liquidGroup = [
            self._ui.surfaceTensionLabel,
            self._ui.surfaceTension,
            self._ui.saturationPressureLabel,
            self._ui.saturationPressure,
        ]

        self._solidGroup = [
            self._ui.emissivityLabel,
            self._ui.emissivity,
        ]

        self._setup(material)
        self._connectSignalsSlots()

    def _setup(self, material):
        self._ui.material.setText(material.name + " (" + material.phase.name + ")")
        self._setGroupVisible(self._fluidGroup, material.phase != Material.PHASE.Solid)
        self._setGroupVisible(self._gasGroup, material.phase == Material.PHASE.Gas)
        self._setGroupVisible(self._liquidGroup, material.phase == Material.PHASE.Liquid)
        self._setGroupVisible(self._solidGroup, material.phase == Material.PHASE.Solid)
        self._resizeDialog(self._ui.propertiesGroup)

        self._ui.densityEdit.setEnabled(False)
        self._ui.specificHeatEdit.setEnabled(False)
        self._ui.viscosityEdit.setEnabled(False)
        self._ui.thermalConductivityEdit.setEnabled(False)

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
        self._ui.densityEdit.setEnabled(index != 0)
        self._ui.constantDensity.setEnabled(index == 0)

    def _specificHeatTypeChanged(self, index):
        self._ui.specificHeatEdit.setEnabled(index != 0)
        self._ui.constantSpecificHeat.setEnabled(index == 0)

    def _viscosityTypeChanged(self, index):
        self._ui.viscosityEdit.setEnabled(index != 0)
        self._ui.constantViscosity.setEnabled(index == 0)

    def _thermalConductivityTypeChanged(self, index):
        self._ui.thermalConductivityEdit.setEnabled(index != 0)
        self._ui.constantThermalConductivity.setEnabled(index == 0)

    def _editDensity(self):
        pass

    def _editSpecificHeat(self):
        dialog = PolynomialDialog(self.tr("Specific Heat"))
        dialog.exec()

    def _editViscosity(self):
        if self._ui.viscosityType.currentIndex() == 1:
            dialog = SutherlandDialog()
            dialog.exec()
        elif self._ui.viscosityType.currentIndex() == 2:
            dialog = PolynomialDialog(self.tr("Viscosity"))
            dialog.exec()

    def _editThermalConductivity(self):
        dialog = PolynomialDialog(self.tr("Specific Heat"))
        dialog.exec()
