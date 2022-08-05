#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QCoreApplication

from coredb import coredb
from coredb.models_db import ModelsDB, TurbulenceModel
from coredb.general_db import GeneralDB
from coredb.material_db import MaterialDB, ListIndex, Phase


class Field(Enum):
    PRESSURE = "pressure"
    SPEED = "speed"
    X_VELOCITY = "xVelocity"
    Y_VELOCITY = "yVelocity"
    Z_VELOCITY = "zVelocity"
    TURBULENT_KINETIC_ENERGY = "turbulentKineticEnergy"
    TURBULENT_DISSIPATION_RATE = "turbulentDissipationRate"
    SPECIFIC_DISSIPATION_RATE = "specificDissipationRate"
    MODIFIED_TURBULENT_VISCOSITY = "modifiedTurbulentViscosity"
    TEMPERATURE = "temperature"
    DENSITY = "density"
    MODIFIED_PRESSURE = "modifiedPressure"
    MATERIAL = "material"


class SurfaceReportType(Enum):
    AREA_WEIGHTED_AVERAGE = "areaWeightedAverage"
    INTEGRAL = "Integral"
    FLOW_RATE = "flowRate"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    COEFFICIENT_OF_VARIATION = "cov"


class VolumeReportType(Enum):
    VOLUME_AVERAGE = "volumeAverage"
    VOLUME_INTEGRAL = "volumeIntegral"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    COEFFICIENT_OF_VARIATION = "cov"


class MonitorDB:
    FORCE_MONITORS_XPATH = './/monitors/forces'
    POINT_MONITORS_XPATH = './/monitors/points'
    SURFACE_MONITORS_XPATH = './/monitors/surfaces'
    VOLUME_MONITORS_XPATH = './/monitors/volumes'

    @classmethod
    def getForceMonitorXPath(cls, name):
        return f'{cls.FORCE_MONITORS_XPATH}/forceMonitor[name="{name}"]'

    @classmethod
    def getPointMonitorXPath(cls, name):
        return f'{cls.POINT_MONITORS_XPATH}/pointMonitor[name="{name}"]'

    @classmethod
    def getSurfaceMonitorXPath(cls, name):
        return f'{cls.SURFACE_MONITORS_XPATH}/surfaceMonitor[name="{name}"]'

    @classmethod
    def getVolumeMonitorXPath(cls, name):
        return f'{cls.VOLUME_MONITORS_XPATH}/volumeMonitor[name="{name}"]'


class FieldHelper:
    FIELD_TEXTS = {
        Field.PRESSURE: QCoreApplication.translate("MonitorField", "Pressure"),
        Field.SPEED: QCoreApplication.translate("MonitorField", "Speed"),
        Field.X_VELOCITY: QCoreApplication.translate("MonitorField", "X-Velocity"),
        Field.Y_VELOCITY: QCoreApplication.translate("MonitorField", "Y-Velocity"),
        Field.Z_VELOCITY: QCoreApplication.translate("MonitorField", "Z-Velocity"),
        Field.TURBULENT_KINETIC_ENERGY: QCoreApplication.translate("MonitorField", "Turbulent Kinetic Energy"),
        Field.TURBULENT_DISSIPATION_RATE: QCoreApplication.translate("MonitorField", "Turbulent Dissipation Rate"),
        Field.SPECIFIC_DISSIPATION_RATE: QCoreApplication.translate("MonitorField", "Specific Dissipation Rate"),
        Field.MODIFIED_TURBULENT_VISCOSITY: QCoreApplication.translate("MonitorField", "Modified Turbulent Viscosity"),
        Field.TEMPERATURE: QCoreApplication.translate("MonitorField", "Temperature"),
        Field.DENSITY: QCoreApplication.translate("MonitorField", "Density"),
        Field.MODIFIED_PRESSURE: QCoreApplication.translate("MonitorField", "Modified Pressure"),
        Field.MATERIAL: QCoreApplication.translate("MonitorField", "material"),
    }

    class FieldItem:
        class DBFieldKey:
            def __init__(self, field, mid=1):
                # Values for coreDB's field element
                self._field = field.value
                self._mid = mid

            @property
            def field(self):
                return self._field

            @property
            def mid(self):
                return self._mid

        def __init__(self, text, field, mid='1'):
            self._text = text
            self._key = self.DBFieldKey(field, mid)

        @property
        def text(self):
            return self._text

        @property
        def key(self):
            return self._key

    @classmethod
    def getAvailableFields(cls):
        fields = []

        def _appendField(field):
            fields.append(cls.FieldItem(cls.FIELD_TEXTS[field], field))

        def _appendMaterial(material):
            fields.append(
                cls.FieldItem(material[ListIndex.NAME.value], Field.MATERIAL, str(material[ListIndex.ID.value])))

        # Always available fields
        _appendField(Field.PRESSURE)
        _appendField(Field.SPEED)
        _appendField(Field.X_VELOCITY)
        _appendField(Field.Y_VELOCITY)
        _appendField(Field.Z_VELOCITY)

        # Fields depending on the turbulence model
        turbulenceModel = ModelsDB.getTurbulenceModel()
        if turbulenceModel == TurbulenceModel.K_EPSILON:
            _appendField(Field.TURBULENT_KINETIC_ENERGY)
            _appendField(Field.TURBULENT_DISSIPATION_RATE)
        elif turbulenceModel == TurbulenceModel.K_OMEGA:
            _appendField(Field.TURBULENT_KINETIC_ENERGY)
            _appendField(Field.SPECIFIC_DISSIPATION_RATE)
        elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
            _appendField(Field.MODIFIED_TURBULENT_VISCOSITY)

        # Fields depending on the energy model
        energyOn = ModelsDB.isEnergyModelOn()
        if energyOn:
            _appendField(Field.TEMPERATURE)
            _appendField(Field.DENSITY)

        # Fields depending on another models
        if (not GeneralDB.isCompressible() and energyOn) or ModelsDB.isMultiphaseModelOn():
            _appendField(Field.MODIFIED_PRESSURE)

        # Material fields when species model is on
        if ModelsDB.isSpeciesModelOn():
            for m in coredb.CoreDB().getMaterials():
                if MaterialDB.DBTextToPhase(m[ListIndex.PHASE.value]) != Phase.SOLID:
                    _appendMaterial(m)

        return fields

    @classmethod
    def DBFieldKeyToText(cls, field, mid):
        if field == Field.MATERIAL.value:
            return coredb.CoreDB().getValue(MaterialDB.getXPath(mid) + '/name')
        else:
            return cls.FIELD_TEXTS[Field(field)]
