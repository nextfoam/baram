#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
from baramFlow.coredb.material_db import MaterialDB, Phase
from baramFlow.openfoam.solver import findSolver, getSolverCapability


class Field(Enum):
    PRESSURE = 'pressure'
    SPEED = 'speed'
    X_VELOCITY = 'xVelocity'
    Y_VELOCITY = 'yVelocity'
    Z_VELOCITY = 'zVelocity'
    TURBULENT_KINETIC_ENERGY = 'turbulentKineticEnergy'
    TURBULENT_DISSIPATION_RATE = 'turbulentDissipationRate'
    SPECIFIC_DISSIPATION_RATE = 'specificDissipationRate'
    MODIFIED_TURBULENT_VISCOSITY = 'modifiedTurbulentViscosity'
    TEMPERATURE = 'temperature'
    DENSITY = 'density'
    MATERIAL = 'material'


class SurfaceReportType(Enum):
    AREA_WEIGHTED_AVERAGE = 'areaWeightedAverage'
    MASS_WEIGHTED_AVERAGE = 'massWeightedAverage'
    INTEGRAL = 'Integral'
    MASS_FLOW_RATE = 'massFlowRate'
    VOLUME_FLOW_RATE = 'volumeFlowRate'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    COEFFICIENT_OF_VARIATION = 'cov'


class VolumeReportType(Enum):
    VOLUME_AVERAGE = 'volumeAverage'
    VOLUME_INTEGRAL = 'volumeIntegral'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    COEFFICIENT_OF_VARIATION = 'cov'


class MonitorDB:
    FORCE_MONITORS_XPATH = './/monitors/forces'
    POINT_MONITORS_XPATH = './/monitors/points'
    SURFACE_MONITORS_XPATH = './/monitors/surfaces'
    VOLUME_MONITORS_XPATH = './/monitors/volumes'

    _surfaceReportTypes = {
        SurfaceReportType.AREA_WEIGHTED_AVERAGE.value: QCoreApplication.translate('MonitorDB', 'Area-Weighted Average'),
        SurfaceReportType.MASS_WEIGHTED_AVERAGE.value: QCoreApplication.translate('MonitorDB', 'Mass-Weighted Average'),
        SurfaceReportType.INTEGRAL.value: QCoreApplication.translate('MonitorDB', 'Integral'),
        SurfaceReportType.MASS_FLOW_RATE.value: QCoreApplication.translate('MonitorDB', 'Mass Flow Rate'),
        SurfaceReportType.VOLUME_FLOW_RATE.value: QCoreApplication.translate('MonitorDB', 'Volume Flow Rate'),
        SurfaceReportType.MINIMUM.value: QCoreApplication.translate('MonitorDB', 'Minimum'),
        SurfaceReportType.MAXIMUM.value: QCoreApplication.translate('MonitorDB', 'Maximum'),
        SurfaceReportType.COEFFICIENT_OF_VARIATION.value:
            QCoreApplication.translate('MonitorDB', 'Coefficient of Variation, CoV'),
    }

    _volumeReportTypes = {
        VolumeReportType.VOLUME_AVERAGE.value: QCoreApplication.translate('MonitorDB', 'Volume Average'),
        VolumeReportType.VOLUME_INTEGRAL.value: QCoreApplication.translate('MonitorDB', 'Volume Integral'),
        VolumeReportType.MINIMUM.value: QCoreApplication.translate('MonitorDB', 'Minimum'),
        VolumeReportType.MAXIMUM.value: QCoreApplication.translate('MonitorDB', 'Maximum'),
        VolumeReportType.COEFFICIENT_OF_VARIATION.value:
            QCoreApplication.translate('MonitorDB', 'Coefficient of Variation, CoV'),
    }

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

    @classmethod
    def dbSurfaceReportTypeToText(cls, dbText):
        return cls._surfaceReportTypes[dbText]

    @classmethod
    def dbVolumeReportTypeToText(cls, dbText):
        return cls._volumeReportTypes[dbText]


class FieldHelper:
    FIELD_TEXTS = {
        Field.PRESSURE: QCoreApplication.translate('MonitorField', 'Pressure'),
        Field.SPEED: QCoreApplication.translate('MonitorField', 'Speed'),
        Field.X_VELOCITY: QCoreApplication.translate('MonitorField', 'X-Velocity'),
        Field.Y_VELOCITY: QCoreApplication.translate('MonitorField', 'Y-Velocity'),
        Field.Z_VELOCITY: QCoreApplication.translate('MonitorField', 'Z-Velocity'),
        Field.TURBULENT_KINETIC_ENERGY: QCoreApplication.translate('MonitorField', 'Turbulent Kinetic Energy'),
        Field.TURBULENT_DISSIPATION_RATE: QCoreApplication.translate('MonitorField', 'Turbulent Dissipation Rate'),
        Field.SPECIFIC_DISSIPATION_RATE: QCoreApplication.translate('MonitorField', 'Specific Dissipation Rate'),
        Field.MODIFIED_TURBULENT_VISCOSITY: QCoreApplication.translate('MonitorField', 'Modified Turbulent Viscosity'),
        Field.TEMPERATURE: QCoreApplication.translate('MonitorField', 'Temperature'),
        Field.DENSITY: QCoreApplication.translate('MonitorField', 'Density'),
        Field.MATERIAL: QCoreApplication.translate('MonitorField', 'material'),
    }

    FIELDS = {
        Field.PRESSURE: 'p',
        Field.SPEED: 'mag(U)',
        Field.X_VELOCITY: 'Ux',
        Field.Y_VELOCITY: 'Uy',
        Field.Z_VELOCITY: 'Uz',
        Field.TURBULENT_KINETIC_ENERGY: 'k',
        Field.TURBULENT_DISSIPATION_RATE: 'epsilon',
        Field.SPECIFIC_DISSIPATION_RATE: 'omega',
        Field.MODIFIED_TURBULENT_VISCOSITY: 'nuTilda',
        Field.TEMPERATURE: 'T',
        Field.DENSITY: 'rho',
    }

    class FieldItem:
        class DBFieldKey:
            def __init__(self, field, mid='1'):
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

        def _appendMaterial(mid, name):
            fields.append(cls.FieldItem(name, Field.MATERIAL, str(mid)))

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

        # Material fields on multiphase model
        if ModelsDB.isMultiphaseModelOn():
            for mid, name, formula, phase in coredb.CoreDB().getMaterials():
                if MaterialDB.dbTextToPhase(phase) != Phase.SOLID:
                    _appendMaterial(mid, name)

        return fields

    @classmethod
    def DBFieldKeyToText(cls, field, mid):
        if field == Field.MATERIAL.value:
            return MaterialDB.getName(mid)
        else:
            return cls.FIELD_TEXTS[Field(field)]

    @classmethod
    def DBFieldKeyToField(cls, field, mid):
        if field == Field.MATERIAL.value:
            return 'alpha.' + MaterialDB.getName(mid)
        else:
            fieldName = cls.FIELDS[Field(field)]

            if fieldName == 'p':
                try:
                    cap = getSolverCapability(findSolver())
                    if cap['usePrgh']:
                        fieldName = 'p_rgh'
                except RuntimeError:
                    pass

            return fieldName
