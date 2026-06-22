#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

import qasync
from PySide6.QtWidgets import QWidget

from libbaram.pfloat import PFloat
from widgets.enum_button_group import EnumButtonGroup
from widgets.simple_sheet_dialog import SimpleSheetDialog

from baramFlow.base.base import SpatialScalarList, TemporalScalarList
from baramFlow.base.boundary.temperature import TemperatureProfile, BoundaryTemperature, \
    TemperatureTemporalDistributionSpecification, TemperatureTemporalDistribution
from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.view.widgets.number_input_dialog import PolynomialDialog
from .temperature_widget_ui import Ui_temperatureWidget


class TemperatureWidget(QWidget):
    RELATIVE_XPATH = '/temperature'

    def __init__(self, xpath, bcid):
        super().__init__()
        self._ui = Ui_temperatureWidget()
        self._ui.setupUi(self)

        self._temporalDistributionRadios = EnumButtonGroup()

        self._bcid = bcid
        self._on = ModelsDB.isEnergyModelOn()

        self._xpath = xpath + self.RELATIVE_XPATH
        self._piecewiseLinear = None
        self._polynomial = None
        self._spatialDistribution = None

        self._dialog = None

        self._ui.profileType.addItem(self.tr("Constant"), TemperatureProfile.CONSTANT)
        self._ui.profileType.addItem(self.tr("Spatial Distribution"), TemperatureProfile.SPATIAL_DISTRIBUTION)
        self._ui.profileType.addItem(self.tr("Temporal Distribution"), TemperatureProfile.TEMPORAL_DISTRIBUTION)

        self._temporalDistributionRadios.addEnumButton(self._ui.piecewiseLinear,
                                                       TemperatureTemporalDistributionSpecification.PIECEWISE_LINEAR)
        self._temporalDistributionRadios.addEnumButton(self._ui.polynomial,
                                                       TemperatureTemporalDistributionSpecification.POLYNOMIAL)

        self._connectSignalsSlots()

    def on(self):
        return self._on

    def data(self):
        if not self._on:
            return None

        data = BoundaryTemperature(profile=self._ui.profileType.currentData())

        if data.profile == TemperatureProfile.CONSTANT:
            data.constant = str(PFloat(self._ui.temperature.text(), self.tr("Temperature")))
        elif data.profile == TemperatureProfile.SPATIAL_DISTRIBUTION:
            data.spatialDistribution = self._spatialDistribution
        elif data.profile == TemperatureProfile.TEMPORAL_DISTRIBUTION:
            specification =self._temporalDistributionRadios.checkedData()
            if specification == TemperatureTemporalDistributionSpecification.PIECEWISE_LINEAR:
                data.temporalDistribution = TemperatureTemporalDistribution(specification=specification,
                                                                            piecewiseLinear=self._piecewiseLinear)
            elif specification == TemperatureTemporalDistributionSpecification.POLYNOMIAL:
                data.temporalDistribution = TemperatureTemporalDistribution(specification=specification,
                                                                            polynomial=self._polynomial)

        return data

    def load(self):
        if not self._on:
            return

        db = coredb.CoreDB()
        self._ui.profileType.setCurrentIndex(
            self._ui.profileType.findData(TemperatureProfile(db.getValue(self._xpath + '/profile'))))
        self._ui.temperature.setText(db.getValue(self._xpath + '/constant'))
        self._temporalDistributionRadios.setCheckedData(
            TemperatureTemporalDistributionSpecification(db.getValue(self._xpath + '/temporalDistribution/specification')))

        self._profileTypeChanged()

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

        profile = self._ui.profileType.currentData()
        writer.append(self._xpath + '/profile', profile.value, None)

        if profile == TemperatureProfile.CONSTANT:
            writer.append(self._xpath + '/constant', self._ui.temperature.text(), self.tr("Temperature"))
        else:   # Only Velocity Inlet.
            pass

        return True

    def _connectSignalsSlots(self):
        self._ui.profileType.currentIndexChanged.connect(self._profileTypeChanged)
        self._ui.spatialDistributionEdit.clicked.connect(self._onSpatialDistributionEdit)
        self._temporalDistributionRadios.selectionChanged.connect(self._onTemporalDistributionTypeChanged)
        self._ui.piecewiseLinearEdit.clicked.connect(self._onPiecewiseLinearEdit)
        self._ui.polynomialEdit.clicked.connect(self._onPolynomialEdit)

    def _profileTypeChanged(self):
        profile = self._ui.profileType.currentData()
        self._ui.constant.setVisible(profile == TemperatureProfile.CONSTANT)
        self._ui.spatialDistribution.setVisible(profile == TemperatureProfile.SPATIAL_DISTRIBUTION)
        self._ui.temporalDistribution.setVisible(profile == TemperatureProfile.TEMPORAL_DISTRIBUTION)

    @qasync.asyncSlot()
    async def _onSpatialDistributionEdit(self):
        if self._spatialDistribution is None:
            self._spatialDistribution = SpatialScalarList.fromElement(
                coredb.CoreDB().getElement(self._xpath + '/spatialDistribution'))

        dialog = SimpleSheetDialog(self, self.tr('Spatial Distribution'), ['x', 'y', 'z', 'T'],
                                   self._spatialDistribution.data())
        try:
            self._spatialDistribution = SpatialScalarList(await dialog.show())
        except asyncio.exceptions.CancelledError:
            return

    def _onTemporalDistributionTypeChanged(self, type_):
        self._ui.piecewiseLinearEdit.setEnabled(type_ == TemperatureTemporalDistributionSpecification.PIECEWISE_LINEAR)
        self._ui.polynomialEdit.setEnabled(type_ == TemperatureTemporalDistributionSpecification.POLYNOMIAL)

    @qasync.asyncSlot()
    async def _onPiecewiseLinearEdit(self):
        if self._piecewiseLinear is None:
            self._piecewiseLinear = TemporalScalarList.fromElement(
                coredb.CoreDB().getElement(self._xpath + '/temporalDistribution/piecewiseLinear'))

        dialog = SimpleSheetDialog(self, self.tr('Spatial Distribution'), ['t', 'T'],
                                   self._piecewiseLinear.data())
        try:
            self._piecewiseLinear = TemporalScalarList(await dialog.show())
        except asyncio.exceptions.CancelledError:
            return

    def _onPolynomialEdit(self):
        if self._polynomial is None:
            db = coredb.CoreDB()
            self._polynomial = db.getValue(self._xpath + '/temporalDistribution/polynomial')

        self._dialog = PolynomialDialog(self, self.tr('Temporal Distribution'), self._polynomial.split(), "a")
        self._dialog.accepted.connect(self._polynomialAccepted)
        self._dialog.open()

    def _piecewiseLinearAccepted(self):
        self._piecewiseLinear = self._dialog.getValues()

    def _polynomialAccepted(self):
        self._polynomial = self._dialog.getValues()

    def freezeProfileToConstant(self):
        self._ui.profileType.setCurrentIndex(0)
        self._ui.profileType.setEnabled(False)
