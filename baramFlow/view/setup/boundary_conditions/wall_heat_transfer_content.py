#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from uuid import UUID

import pandas as pd
import qasync
from PySide6.QtWidgets import QWidget

from libbaram.natural_name_uuid import uuidToNnstr
from libbaram.pfloat import PFloat
from widgets.simple_sheet_dialog import SimpleSheetDialog

from baramFlow.base.base import TrackedData
from baramFlow.base.boundary.wall import WallHeatTransfer
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import WallHeatTransferMode
from baramFlow.coredb.project import Project
from baramFlow.view.setup.boundary_conditions.wall_heat_transfer_content_ui import Ui_WallHeatTransferContent


class WallHeatTransferContent(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_WallHeatTransferContent()
        self._ui.setupUi(self)

        self._temperatureDistributionName = None
        self._temperatureDistribution = TrackedData()

        self._connectSignalsSlots()

        self._ui.mode.addItem(self.tr('Adiabatic'), WallHeatTransferMode.ADIABATIC)
        self._ui.mode.addItem(self.tr('Constant Temperature'), WallHeatTransferMode.CONSTANT_TEMPERATURE)
        self._ui.mode.addItem(self.tr('Temperature Distribution'), WallHeatTransferMode.TEMPERATURE_DISTRIBUTION)
        self._ui.mode.addItem(self.tr('Constant Heat Flux'), WallHeatTransferMode.CONSTANT_HEAT_FLUX)
        self._ui.mode.addItem(self.tr('Convection and Radiation'), WallHeatTransferMode.CONVECTION)

        parent.layout().addWidget(self)

    def data(self):
        mode=self._ui.mode.currentData()

        data = WallHeatTransfer(mode=self._ui.mode.currentData())
        if mode == WallHeatTransferMode.CONSTANT_TEMPERATURE:
            data.temperature = self._ui.temperature.pFloat(self.tr('Temperature'))
        elif mode == WallHeatTransferMode.TEMPERATURE_DISTRIBUTION:
            if self._temperatureDistribution.isNone() and self._temperatureDistributionName.int == 0:
                raise ValueError(self.tr('Edit Temperature Distribution.'))

            if self._temperatureDistribution.isModified():
                data.temperatureDistribution = pd.DataFrame(self._temperatureDistribution.data())
        elif mode == WallHeatTransferMode.CONSTANT_HEAT_FLUX:
            data.heatFlux = self._ui.heatFlux.pFloat(self.tr('Temperature'))
            data.heatFlux = PFloat(self._ui.heatFlux.text(), self.tr('Temperature'))
        elif mode == WallHeatTransferMode.CONVECTION:
            data.heatTransferCoefficient = self._ui.heatTransferCoefficient.pFloat(self.tr('Heat Transfer Coefficient'))
            data.freeStreamTemperature = self._ui.freeStreamTemperature.pFloat(self.tr('Free Stream Temperature'))
            data.externalEmissivity = self._ui.externalEmissivity.pFloat(self.tr('External Emissivity'), low=0, high=1)
            data.wallLayers = self._ui.wallLayers.data()

        return data

    def _connectSignalsSlots(self):
        self._ui.mode.currentIndexChanged.connect(self._onModeChanged)
        self._ui.editTemperatureDistribution.clicked.connect(self._onEditTemperatureDistribution)

    def load(self, xpath):
        db = coredb.CoreDB()

        self._setMode(WallHeatTransferMode(db.getValue(xpath + '/type')))
        self._ui.temperature.setText(db.getValue(xpath + '/temperature'))
        self._temperatureDistributionName = UUID(db.getValue(xpath + '/temperatureDistributionName'))
        self._ui.heatFlux.setText(db.getValue(xpath + '/heatFlux'))
        self._ui.heatTransferCoefficient.setText(db.getValue(xpath + '/heatTransferCoefficient'))
        self._ui.freeStreamTemperature.setText(db.getValue(xpath + '/freeStreamTemperature'))
        self._ui.externalEmissivity.setText(db.getValue(xpath + '/externalEmissivity'))
        self._ui.wallLayers.load(xpath + '/wallLayers')

    def _setMode(self, mode):
        self._ui.mode.setCurrentIndex(self._ui.mode.findData(mode))
        self._onModeChanged()

    def _onModeChanged(self):
        mode = self._ui.mode.currentData()

        self._ui.constantTemperature.setVisible(mode == WallHeatTransferMode.CONSTANT_TEMPERATURE)
        self._ui.temperatureDistribution.setVisible(mode == WallHeatTransferMode.TEMPERATURE_DISTRIBUTION)
        self._ui.constantHeatFlux.setVisible(mode == WallHeatTransferMode.CONSTANT_HEAT_FLUX)
        self._ui.convection.setVisible(mode == WallHeatTransferMode.CONVECTION)

    @qasync.asyncSlot()
    async def _onEditTemperatureDistribution(self):
        if self._temperatureDistribution.isNone() and self._temperatureDistributionName.int != 0:
            self._temperatureDistribution = TrackedData(
                Project.instance().fileDB().getDataFrame(uuidToNnstr(self._temperatureDistributionName)).values.tolist())

        dialog = SimpleSheetDialog(
            self, self.tr('Temperature Distribution'), ['x', 'y', 'z', 't'], self._temperatureDistribution.data())
        try:
            self._temperatureDistribution.setData(await dialog.show())
        except asyncio.exceptions.CancelledError:
            return
