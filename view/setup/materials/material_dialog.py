#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.widgets.resizable_dialog import ResizableDialog
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.number_input_dialog import PolynomialDialog
from .material_db import MaterialDB, Specification, Phase
from .material_dialog_ui import Ui_MaterialDialog


class PropertyFormRow(Enum):
    MOLECULAR_WEIGHT = 0
    ABSORPTION_COEFFICIENT = auto()
    SURFACE_TENSION = auto()
    SATURATION_PRESSURE = auto()
    EMISSIVITY = auto()


class MaterialDialog(ResizableDialog):
    _propertyFormRows = {
        PropertyFormRow.MOLECULAR_WEIGHT.value: Phase.FLUID,
        PropertyFormRow.ABSORPTION_COEFFICIENT.value: Phase.GAS,
        PropertyFormRow.SURFACE_TENSION.value: Phase.LIQUID,
        PropertyFormRow.SATURATION_PRESSURE.value: Phase.LIQUID,
        PropertyFormRow.EMISSIVITY.value: Phase.SOLID,
    }

    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_MaterialDialog()
        self._ui.setupUi(self)

        self._specifications = {
            Specification.CONSTANT: self.tr("constant"),
            Specification.PERFECT_GAS: self.tr("perfect gas"),
            Specification.SUTHERLAND: self.tr("sutherland"),
            Specification.POLYNOMIAL: self.tr("polynomial")
        }

        self._xpath = xpath
        self._db = coredb.CoreDB()
        self._phase = MaterialDB.getPhase(self._db.getValue(self._xpath + '/phase'))
        self._polynomialSpecificHeat = None
        self._polynomialViscosity = None
        self._polynomialThermalConductivity = None
        self._polynomialDialog = None

        self._showPropertyRows()
        self._setupSpecifications()
        self._ui.viscosityGroup.setVisible(self._phase != Phase.SOLID)

        self._connectSignalsSlots()

    def showEvent(self, event):
        self._ui.material.setText(self._db.getValue(self._xpath + '/name'))

        specification = MaterialDB.getSpecification(self._db.getValue(self._xpath + '/density/specification'))
        self._ui.densityType.setCurrentText(self._specifications[specification])
        self._ui.constantDensity.setText(self._db.getValue(self._xpath + '/density/constant'))
        self._densityTypeChanged()

        specification = MaterialDB.getSpecification(self._db.getValue(self._xpath + '/specificHeat/specification'))
        self._ui.specificHeatType.setCurrentText(self._specifications[specification])
        self._ui.constantSpecificHeat.setText(self._db.getValue(self._xpath + '/specificHeat/constant'))
        self._specificHeatTypeChanged()

        if self._phase != Phase.SOLID:
            specification = MaterialDB.getSpecification(self._db.getValue(self._xpath + '/viscosity/specification'))
            self._ui.viscosityType.setCurrentText(self._specifications[specification])
            self._ui.constantViscosity.setText(self._db.getValue(self._xpath + '/viscosity/constant'))
            if self._phase == Phase.GAS:
                self._ui.sutherlandCoefficient.setText(
                    self._db.getValue(self._xpath + '/viscosity/sutherland/coefficient'))
                self._ui.sutherlandTemperature.setText(
                    self._db.getValue(self._xpath + '/viscosity/sutherland/temperature'))
            self._viscosityTypeChanged()

        specification = MaterialDB.getSpecification(
            self._db.getValue(self._xpath + '/thermalConductivity/specification'))
        self._ui.thermalConductivityType.setCurrentText(self._specifications[specification])
        self._ui.constantThermalConductivity.setText(self._db.getValue(self._xpath + '/thermalConductivity/constant'))
        self._thermalConductivityTypeChanged()

        if self._phase != Phase.SOLID:
            self._ui.molecularWeight.setText(self._db.getValue(self._xpath + '/molecularWeight'))
        if self._phase == Phase.GAS:
            self._ui.absorptionCoefficient.setText(self._db.getValue(self._xpath + '/absorptionCoefficient'))
        if self._phase == Phase.LIQUID:
            self._ui.surfaceTension.setText(self._db.getValue(self._xpath + '/surfaceTension'))
            self._ui.saturationPressure.setText(self._db.getValue(self._xpath + '/saturationPressure'))
        if self._phase == Phase.SOLID:
            self._ui.emissivity.setText(self._db.getValue(self._xpath + '/emissivity'))

    def accept(self):
        writer = CoreDBWriter()

        specification = self._ui.densityType.currentData()
        writer.append(self._xpath + '/density/specification', specification.value, None)
        if specification == Specification.CONSTANT:
            writer.append(self._xpath + '/density/constant', self._ui.constantDensity.text(), self.tr("Density Value"))

        specification = self._ui.specificHeatType.currentData()
        writer.append(self._xpath + '/specificHeat/specification', specification.value, None)
        if specification == Specification.CONSTANT:
            writer.append(self._xpath + '/specificHeat/constant',
                          self._ui.constantSpecificHeat.text(), self.tr("Specific Heat Value"))
        elif specification == Specification.POLYNOMIAL:
            if self._polynomialSpecificHeat is not None:
                writer.append(self._xpath + '/specificHeat/polynomial',
                              self._polynomialSpecificHeat[0], self.tr("Specific Heat Polynomial"))
            elif self._db.getValue(self._xpath + '/specificHeat/polynomial') == '':
                QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Specific Heat Polynomial."))
                return

        if self._phase != Phase.SOLID:
            specification = self._ui.viscosityType.currentData()
            writer.append(self._xpath + '/viscosity/specification', specification.value, None)
            if specification == Specification.CONSTANT:
                writer.append(self._xpath + '/viscosity/constant',
                              self._ui.constantViscosity.text(), self.tr("Viscosity Value"))
            elif specification == Specification.SUTHERLAND:
                writer.append(self._xpath + '/viscosity/sutherland/coefficient',
                              self._ui.sutherlandCoefficient.text(), self.tr("Sutherland Coefficient"))
                writer.append(self._xpath + '/viscosity/sutherland/temperature',
                              self._ui.sutherlandTemperature.text(), self.tr("Sutherland Temperature"))
            elif specification == Specification.POLYNOMIAL:
                if self._polynomialViscosity is not None:
                    writer.append(self._xpath + '/viscosity/polynomial',
                                  self._polynomialViscosity[0], self.tr("Viscosity Polynomial"))
                elif self._db.getValue(self._xpath + '/viscosity/polynomial') == '':
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Viscosity Polynomial."))
                    return

        specification = self._ui.thermalConductivityType.currentData()
        writer.append(self._xpath + '/thermalConductivity/specification', specification.value, None)
        if specification == Specification.CONSTANT:
            writer.append(self._xpath + '/thermalConductivity/constant',
                          self._ui.constantThermalConductivity.text(), self.tr("Thermal Conductivity Value"))
        elif specification == Specification.POLYNOMIAL:
            if self._polynomialThermalConductivity is not None:
                writer.append(self._xpath + '/thermalConductivity/polynomial',
                              self._polynomialThermalConductivity[0], self.tr("Thermal Conductivity Polynomial"))
            elif self._db.getValue(self._xpath + '/thermalConductivity/polynomial') == '':
                QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Thermal Conductivity Polynomial."))
                return

        if self._phase != Phase.SOLID:
            writer.append(self._xpath + '/molecularWeight',
                          self._ui.molecularWeight.text(), self.tr("Molecular Weight"))
        if self._phase == Phase.GAS:
            writer.append(self._xpath + '/absorptionCoefficient',
                          self._ui.absorptionCoefficient.text(), self.tr("Absorption Coefficient"))
        if self._phase == Phase.LIQUID:
            writer.append(self._xpath + '/surfaceTension', self._ui.surfaceTension.text(), self.tr("Surface Tension"))
            writer.append(self._xpath + '/saturationPressure',
                          self._ui.saturationPressure.text(), self.tr("Surface Pressure"))
        if self._phase == Phase.SOLID:
            writer.append(self._xpath + '/emissivity', self._ui.emissivity.text(), self.tr("Emissivity"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.close()

    def _showPropertyRows(self):
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
            if p & self._phase:
                form.addRow(rows[i][0], rows[i][1])

    def _setupSpecifications(self):
        if self._phase == Phase.GAS:
            self._setupSpecificationCombo(
                self._ui.densityType, [
                    Specification.CONSTANT,
                    Specification.PERFECT_GAS
                ]
            )
        else:
            self._setupSpecificationCombo(
                self._ui.densityType, [
                    Specification.CONSTANT,
                ]
            )

        self._setupSpecificationCombo(
            self._ui.specificHeatType, [
                Specification.CONSTANT,
                Specification.POLYNOMIAL
            ]
        )

        if self._phase == Phase.GAS:
            self._setupSpecificationCombo(
                self._ui.viscosityType, [
                    Specification.CONSTANT,
                    Specification.SUTHERLAND,
                    Specification.POLYNOMIAL
                ]
            )
        elif self._phase == Phase.LIQUID:
            self._setupSpecificationCombo(
                self._ui.viscosityType, [
                    Specification.CONSTANT,
                    Specification.POLYNOMIAL
                ]
            )

        self._setupSpecificationCombo(
            self._ui.thermalConductivityType, [
                Specification.CONSTANT,
                Specification.POLYNOMIAL
            ]

        )

    def _setupSpecificationCombo(self, combo, types):
        for t in types:
            combo.addItem(self._specifications[t], t)

    def _connectSignalsSlots(self):
        self._ui.densityType.currentTextChanged.connect(self._densityTypeChanged)
        self._ui.specificHeatType.currentTextChanged.connect(self._specificHeatTypeChanged)
        self._ui.viscosityType.currentTextChanged.connect(self._viscosityTypeChanged)
        self._ui.thermalConductivityType.currentTextChanged.connect(self._thermalConductivityTypeChanged)
        self._ui.densityEdit.clicked.connect(self._editDensity)
        self._ui.specificHeatEdit.clicked.connect(self._editSpecificHeat)
        self._ui.viscosityEdit.clicked.connect(self._editViscosity)
        self._ui.thermalConductivityEdit.clicked.connect(self._editThermalConductivity)

    def _densityTypeChanged(self):
        specification = self._ui.densityType.currentData(Qt.UserRole)
        self._ui.densityEdit.setEnabled(specification == Specification.PERFECT_GAS)
        self._ui.constantDensity.setEnabled(specification == Specification.CONSTANT)

    def _specificHeatTypeChanged(self):
        specification = self._ui.specificHeatType.currentData(Qt.UserRole)
        self._ui.specificHeatEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantSpecificHeat.setEnabled(specification == Specification.CONSTANT)

    def _viscosityTypeChanged(self):
        specification = self._ui.viscosityType.currentData(Qt.UserRole)
        self._ui.viscosityEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantViscosity.setEnabled(specification == Specification.CONSTANT)
        self._ui.sutherlandCoefficient.setEnabled(specification == Specification.SUTHERLAND)
        self._ui.sutherlandTemperature.setEnabled(specification == Specification.SUTHERLAND)

    def _thermalConductivityTypeChanged(self):
        specification = self._ui.thermalConductivityType.currentData(Qt.UserRole)
        self._ui.thermalConductivityEdit.setEnabled(specification == Specification.POLYNOMIAL)
        self._ui.constantThermalConductivity.setEnabled(specification == Specification.CONSTANT)

    def _editDensity(self):
        pass

    def _editSpecificHeat(self):
        self._dialog = PolynomialDialog(self.tr("Polynomial Specific Heat"),
                                        self._db.getValue(self._xpath + '/specificHeat/polynomial'))
        self._dialog.accepted.connect(self._polynomialSpeicificHeatAccepted)
        self._dialog.open()

    def _editViscosity(self):
        self._dialog = PolynomialDialog(self.tr("Polynomial Viscosity"),
                                        self._db.getValue(self._xpath + '/viscosity/polynomial'))
        self._dialog.accepted.connect(self._polynomialViscosityAccepted)
        self._dialog.open()

    def _editThermalConductivity(self):
        self._dialog = PolynomialDialog(self.tr("Polynomial Thermal Conductivity"),
                                        self._db.getValue(self._xpath + '/thermalConductivity/polynomial'))
        self._dialog.accepted.connect(self._polynomialThermalConductivityAccepted)
        self._dialog.open()

    def _polynomialSpeicificHeatAccepted(self):
        self._polynomialSpecificHeat = self._dialog.getValues()

    def _polynomialViscosityAccepted(self):
        self._polynomialViscosity = self._dialog.getValues()

    def _polynomialThermalConductivityAccepted(self):
        self._polynomialThermalConductivity = self._dialog.getValues()
