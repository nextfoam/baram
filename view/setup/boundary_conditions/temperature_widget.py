#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox

from coredb import coredb
from view.widgets.number_input_dialog import PiecewiseLinearDialog, PolynomialDialog
from .temperature_widget_ui import Ui_temperatureWidget
from .boundary_db import TemperatureProfile, TemperatureTemporalDistribution


class TemperatureWidget(QWidget):
    RELATIVE_PATH = '/temperature'

    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_temperatureWidget()
        self._ui.setupUi(self)

        self._profileTypes = {
            TemperatureProfile.CONSTANT.value: self.tr("Constant"),
            TemperatureProfile.SPATIAL_DISTRIBUTION.value: self.tr("Spatial Distribution"),
            TemperatureProfile.TEMPORAL_DISTRIBUTION.value: self.tr("Temporal Distribution"),
        }

        self._temporalDistributionRadios = {
            self._ui.temporalDistributionRadioGroup.id(self._ui.piecewiseLinear):
                TemperatureTemporalDistribution.PIECEWISE_LINEAR.value,
            self._ui.temporalDistributionRadioGroup.id(self._ui.polynomial):
                TemperatureTemporalDistribution.POLYNOMIAL.value,
        }

        self._setupProfileTypeCombo()

        self._db = coredb.CoreDB()
        self._xpath = xpath + self.RELATIVE_PATH
        self._piecewiseLinear = None
        self._polynomial = None

        self._connectSignalsSlots()

    def load(self):
        self._ui.profileType.setCurrentText(self._profileTypes[self._db.getValue(self._xpath + '/profile')])
        self._ui.temperature.setText(self._db.getValue(self._xpath + '/constant'))
        self._getRadio(
            self._ui.temporalDistributionRadioGroup, self._temporalDistributionRadios,
            self._db.getValue(self._xpath + '/temporalDistribution/specification')
        ).setChecked(True)
        self._profileTypeChanged()
        self._temporalDistributionTypeChanged()

    def appendToWriter(self, writer):
        profile = self._ui.profileType.currentData()
        writer.append(self._xpath + '/profile', profile, None)

        if profile == TemperatureProfile.CONSTANT.value:
            writer.append(self._xpath + '/constant', self._ui.temperature.text(), self.tr("Temperature"))
        elif profile == TemperatureProfile.SPATIAL_DISTRIBUTION.value:
            pass
        elif profile == TemperatureProfile.TEMPORAL_DISTRIBUTION.value:
            specification = self._getRadioValue(
                self._ui.temporalDistributionRadioGroup, self._temporalDistributionRadios)
            writer.append(self._xpath + '/temporalDistribution/specification', specification, None)
            if specification == TemperatureTemporalDistribution.PIECEWISE_LINEAR.value:
                if self._piecewiseLinear is not None:
                    writer.append(self._xpath + '/temporalDistribution/piecewiseLinear/t',
                                  self._piecewiseLinear[0], self.tr("Piecewise Linear."))
                    writer.append(self._xpath + '/temporalDistribution/piecewiseLinear/v',
                                  self._piecewiseLinear[1], self.tr("Piecewise Linear."))
                elif self._db.getValue(self._xpath + '/temporalDistribution/piecewiseLinear/t') == '':
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Piecewise Linear."))
                    return
            elif specification == TemperatureTemporalDistribution.POLYNOMIAL.value:
                if self._polynomial is not None:
                    writer.append(self._xpath + '/temporalDistribution/polynomial',
                                  self._polynomial, self.tr("Polynomial Linear."))
                elif self._db.getValue(self._xpath + '/temporalDistribution/polynomial') == '':
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Polynomial Linear."))
                    return

    def _connectSignalsSlots(self):
        self._ui.profileType.currentIndexChanged.connect(self._profileTypeChanged)
        self._ui.spatialDistributionFileSelect.clicked.connect(self._selectSpatialDistributionFile)
        self._ui.temporalDistributionRadioGroup.idToggled.connect(self._temporalDistributionTypeChanged)
        self._ui.piecewiseLinearEdit.clicked.connect(self._editPiecewiseLinear)
        self._ui.polynomialEdit.clicked.connect(self._editPolynomial)

    def _setupProfileTypeCombo(self):
        for value, text in self._profileTypes.items():
            self._ui.profileType.addItem(text, value)

    def _profileTypeChanged(self):
        profile = self._ui.profileType.currentData()
        self._ui.constant.setVisible(profile == TemperatureProfile.CONSTANT.value)
        self._ui.spatialDistribution.setVisible(profile == TemperatureProfile.SPATIAL_DISTRIBUTION.value)
        self._ui.temporalDistribution.setVisible(profile == TemperatureProfile.TEMPORAL_DISTRIBUTION.value)

    def _selectSpatialDistributionFile(self):
        fileName = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if fileName[0]:
            self._ui.spatialDistributionFileName.setText(self._xpath.basename(fileName[0]))

    def _temporalDistributionTypeChanged(self):
        self._ui.piecewiseLinearEdit.setEnabled(self._ui.piecewiseLinear.isChecked())
        self._ui.polynomialEdit.setEnabled(self._ui.polynomial.isChecked())

    def _editPiecewiseLinear(self):
        if self._piecewiseLinear is None:
            self._piecewiseLinear = [
                self._db.getValue(self._xpath + '/temporalDistribution/piecewiseLinear/t'),
                self._db.getValue(self._xpath + '/temporalDistribution/piecewiseLinear/v'),
            ]
        self._dialog = PiecewiseLinearDialog(self, self.tr("Temporal Distribution"), [self.tr("t"), self.tr("T")],
                                             self._piecewiseLinear)
        self._dialog.accepted.connect(self._piecewiseLinearAccepted)
        self._dialog.open()

    def _editPolynomial(self):
        if self._polynomial is None:
            self._polynomial = self._db.getValue(self._xpath + '/temporalDistribution/polynomial')

        self._dialog = PolynomialDialog(self, self.tr("Temporal Distribution"), self._polynomial, "a")
        self._dialog.accepted.connect(self._polynomialAccepted)
        self._dialog.open()

    def _piecewiseLinearAccepted(self):
        self._piecewiseLinear = self._dialog.getValues()

    def _polynomialAccepted(self):
        self._polynomial = self._dialog.getValues()

    def _getRadio(self, group, radios, value):
        return group.button(list(radios.keys())[list(radios.values()).index(value)])

    def _getRadioValue(self, group, radios):
        return radios[group.id(group.checkedButton())]
