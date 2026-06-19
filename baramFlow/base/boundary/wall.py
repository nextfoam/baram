#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID

from pandas import DataFrame

from libbaram.pfloat import PFloat

from baramFlow.base.base import UUID_ZERO
from baramFlow.base.boundary.boundary import TemperatureLayers
from baramFlow.base.file_data_manager import FileDataManager
from baramFlow.coredb.boundary_db import WallHeatTransferMode
from baramFlow.coredb.libdb import E, nsmap


@dataclass
class WallHeatTransfer:
    mode: WallHeatTransferMode          = WallHeatTransferMode.ADIABATIC
    temperature: PFloat                 = field(default_factory=lambda: PFloat('300'))
    heatFlux: PFloat                    = field(default_factory=lambda: PFloat('1000'))
    temperatureDistributionName: UUID   = UUID_ZERO
    heatTransferCoefficient: PFloat     = field(default_factory=lambda: PFloat('100'))
    freeStreamTemperature: PFloat       = field(default_factory=lambda: PFloat('300'))
    externalEmissivity: PFloat          = field(default_factory=lambda: PFloat('0'))
    wallLayers: TemperatureLayers       = field(default_factory=TemperatureLayers)

    temperatureDistribution: DataFrame  = None

    def update(self, new):
        self.mode = new.mode

        if new.mode == WallHeatTransferMode.CONSTANT_TEMPERATURE:
            self.temperature = new.temperature
        elif new.mode == WallHeatTransferMode.TEMPERATURE_DISTRIBUTION:
            if new.temperatureDistribution is not None:
                self.temperatureDistributionName = FileDataManager.putDataFrame(new.temperatureDistribution)
            self.temperatureDistribution = new.temperatureDistribution
        elif new.mode == WallHeatTransferMode.CONSTANT_HEAT_FLUX:
            self.heatFlux = new.heatFlux
        elif new.mode == WallHeatTransferMode.CONVECTION:
            self.heatTransferCoefficient = new.heatTransferCoefficient
            self.freeStreamTemperature = new.freeStreamTemperature
            self.externalEmissivity = new.externalEmissivity
            self.wallLayers.update(new.wallLayers)

    def toElement(self):
        return E('heatTransfer',
                 E('type', self.mode),
                 self.temperature.toElement('temperature'),
                 self.heatFlux.toElement('heatFlux'),
                 E('temperatureDistributionName', self.temperatureDistributionName),
                 self.heatTransferCoefficient.toElement('heatTransferCoefficient'),
                 self.freeStreamTemperature.toElement('freeStreamTemperature'),
                 self.externalEmissivity.toElement('externalEmissivity'),
                 self.wallLayers.toElement())

    @staticmethod
    def fromElement(e):
        return WallHeatTransfer(
            mode=WallHeatTransferMode(e.find('type', namespaces=nsmap).text),
            temperature=PFloat.fromElement(e.find('temperature', namespaces=nsmap)),
            heatFlux=PFloat.fromElement(e.find('heatFlux', namespaces=nsmap)),
            temperatureDistributionName=UUID(e.find('temperatureDistributionName', namespaces=nsmap).text),
            heatTransferCoefficient=PFloat.fromElement(e.find('heatTransferCoefficient', namespaces=nsmap)),
            freeStreamTemperature=PFloat.fromElement(e.find('freeStreamTemperature', namespaces=nsmap)),
            externalEmissivity=PFloat.fromElement(e.find('externalEmissivity', namespaces=nsmap)),
            wallLayers=TemperatureLayers.fromElement(e.find('wallLayers', namespaces=nsmap)))


@dataclass
class Wall:
    heatTransfer: WallHeatTransfer = field(default_factory=WallHeatTransfer)

    @staticmethod
    def fromElement(e):
        return Wall(heatTransfer=WallHeatTransfer.fromElement(e.find('heatTransfer', namespaces=nsmap)))
