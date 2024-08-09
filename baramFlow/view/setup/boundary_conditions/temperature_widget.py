#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.filedb import BcFileRole, FileFormatError
from baramFlow.coredb.boundary_db import TemperatureProfile, TemperatureTemporalDistribution
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.project import Project
from baramFlow.view.widgets.number_input_dialog import PiecewiseLinearDialog, PolynomialDialog
from .temperature_widget_ui import Ui_temperatureWidget


class TemperatureWidget(QWidget):
    RELATIVE_XPATH = '/temperature'

    def __init__(self, xpath, bcid):
        super().__init__()
        self._ui = Ui_temperatureWidget()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._on = ModelsDB.isEnergyModelOn()

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

        self._xpath = xpath + self.RELATIVE_XPATH
        self._piecewiseLinear = None
        self._polynomial = None
        self._spatialDistributionFile = None
        self._spatialDistributionFileName = None
        self._spatialDistributionFileKey = None
        self._spatialDistributionFileOldKey = None

        self._dialog = None

        self._connectSignalsSlots()

    def on(self):
        return self._on

    def load(self):
        if not self._on:
            return

        db = coredb.CoreDB()
        self._ui.profileType.setCurrentText(self._profileTypes[db.getValue(self._xpath + '/profile')])
        self._ui.temperature.setText(db.getValue(self._xpath + '/constant'))
        self._getRadio(
            self._ui.temporalDistributionRadioGroup, self._temporalDistributionRadios,
            db.getValue(self._xpath + '/temporalDistribution/specification')
        ).setChecked(True)
        self._spatialDistributionFileName = Project.instance().fileDB().getUserFileName(
            db.getValue(self._xpath + '/spatialDistribution'))
        self._ui.spatialDistributionFileName.setText(self._spatialDistributionFileName)
        self._profileTypeChanged()
        self._temporalDistributionTypeChanged()

    def appendToWriter(self, writer):
        """
        Append this widget's data to the writer so that it is saved by the parent dialog.
        After the writer's writing, it is recommended to call completeWriting or rollbackWriting
        to delete unnecessary spatial distribution file data from the FileDB.

        Args:
            writer: CoreDBWriter created by the dialog containing this widget.

        Returns:
            True if the data is valid, False otherwise

        """
        if not self._on:
            return True

        db = coredb.CoreDB()
        profile = self._ui.profileType.currentData()
        writer.append(self._xpath + '/profile', profile, None)

        if profile == TemperatureProfile.CONSTANT.value:
            writer.append(self._xpath + '/constant', self._ui.temperature.text(), self.tr("Temperature"))
        elif profile == TemperatureProfile.SPATIAL_DISTRIBUTION.value:
            if self._spatialDistributionFile:
                try:
                    self._spatialDistributionFileOldKey = db.getValue(self._xpath + '/spatialDistribution')
                    self._spatialDistributionFileKey = Project.instance().fileDB().putBcFile(
                        self._bcid, BcFileRole.BC_TEMPERATURE, self._spatialDistributionFile)
                    writer.append(self._xpath + '/spatialDistribution', self._spatialDistributionFileKey, None)
                except FileFormatError:
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("CSV File is wrong"))
                    return False
            elif not self._spatialDistributionFileName:
                QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select CSV File."))
                return False
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
                elif db.getValue(self._xpath + '/temporalDistribution/piecewiseLinear/t') == '':
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Piecewise Linear."))
                    return False
            elif specification == TemperatureTemporalDistribution.POLYNOMIAL.value:
                if self._polynomial is not None:
                    writer.append(self._xpath + '/temporalDistribution/polynomial',
                                  self._polynomial, self.tr("Polynomial Linear."))
                elif db.getValue(self._xpath + '/temporalDistribution/polynomial') == '':
                    QMessageBox.critical(self, self.tr("Input Error"), self.tr("Edit Polynomial Linear."))
                    return False

        return True

    def completeWriting(self):
        """
        Delete the old key of the spatial distribution file if it has been updated.
        This function should be called after all the data of the dialog containing this widget has been written to coredb.
        Notice: Since the copy boundary conditions feature has been added, so old key should not be deleted.
        """
        # if self._spatialDistributionFileKey and self._spatialDistributionFileOldKey:
        #     Project.instance().fileDB().delete(self._spatialDistributionFileOldKey)
        return

    def rollbackWriting(self):
        """
        Delete the new key of the spatial distribution file.
        This function should be called if the dialog containing this widget fails to write data to coredb.
        """
        if self._spatialDistributionFileKey:
            Project.instance().fileDB().delete(self._spatialDistributionFileKey)

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
        self._dialog = QFileDialog(self, self.tr('Select CSV File'), '', 'CSV (*.csv)')
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialog.accepted.connect(self._spatialDistributionFileSelected)
        self._dialog.open()

    def _temporalDistributionTypeChanged(self):
        self._ui.piecewiseLinearEdit.setEnabled(self._ui.piecewiseLinear.isChecked())
        self._ui.polynomialEdit.setEnabled(self._ui.polynomial.isChecked())

    def _editPiecewiseLinear(self):
        if self._piecewiseLinear is None:
            db = coredb.CoreDB()
            self._piecewiseLinear = [
                db.getValue(self._xpath + '/temporalDistribution/piecewiseLinear/t'),
                db.getValue(self._xpath + '/temporalDistribution/piecewiseLinear/v'),
            ]
        self._dialog = PiecewiseLinearDialog(self, self.tr("Temporal Distribution"), [self.tr("t"), self.tr("T")],
                                             self._piecewiseLinear)
        self._dialog.accepted.connect(self._piecewiseLinearAccepted)
        self._dialog.open()

    def _editPolynomial(self):
        if self._polynomial is None:
            db = coredb.CoreDB()
            self._polynomial = db.getValue(self._xpath + '/temporalDistribution/polynomial')

        self._dialog = PolynomialDialog(self, self.tr("Temporal Distribution"), self._polynomial, "a")
        self._dialog.accepted.connect(self._polynomialAccepted)
        self._dialog.open()

    def _piecewiseLinearAccepted(self):
        self._piecewiseLinear = self._dialog.getValues()

    def _polynomialAccepted(self):
        self._polynomial = self._dialog.getValues()

    def _getRadio(self, group, radios, value):
        return group.button(list(radios.keys())[list(radios.values()).index(value)])

    def _spatialDistributionFileSelected(self):
        if files := self._dialog.selectedFiles():
            self._spatialDistributionFile = Path(files[0])
            self._ui.spatialDistributionFileName.setText(self._spatialDistributionFile.name)

    def _getRadioValue(self, group, radios):
        return radios[group.id(group.checkedButton())]

    def freezeProfileToConstant(self):
        self._ui.profileType.setCurrentIndex(0)
        self._ui.profileType.setEnabled(False)
