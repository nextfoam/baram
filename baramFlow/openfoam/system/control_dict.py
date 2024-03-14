#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import platform

from libbaram.app_path import APP_PATH
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

import baramFlow.openfoam.solver
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, WallVelocityCondition
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.material_db import MaterialDB, Phase
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, SurfaceReportType, VolumeReportType
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import findSolver, getSolverCapability


SURFACE_MONITOR_OPERATION = {
    SurfaceReportType.AREA_WEIGHTED_AVERAGE.value: 'areaAverage',
    SurfaceReportType.MASS_WEIGHTED_AVERAGE.value: 'average',
    SurfaceReportType.INTEGRAL.value: 'areaIntegrate',
    SurfaceReportType.MASS_FLOW_RATE.value: 'sum',
    SurfaceReportType.VOLUME_FLOW_RATE.value: 'areaNormalIntegrate',
    SurfaceReportType.MINIMUM.value: 'min',
    SurfaceReportType.MAXIMUM.value: 'max',
    SurfaceReportType.COEFFICIENT_OF_VARIATION.value: 'CoV',
}

VOLUME_MONITOR_OPERATION = {
    VolumeReportType.VOLUME_AVERAGE.value: 'volAverage',
    VolumeReportType.VOLUME_INTEGRAL.value: 'volIntegrate',
    VolumeReportType.MINIMUM.value: 'min',
    VolumeReportType.MAXIMUM.value: 'max',
    VolumeReportType.COEFFICIENT_OF_VARIATION.value: 'CoV',
}

_basePath = APP_PATH.joinpath('solvers', 'openfoam', 'lib')
if platform.system() == 'Windows':
    _libExt = '.dll'
elif platform.system() == 'Darwin':
    _libExt = '.dylib'
else:
    _libExt = '.so'


def _libPath(baseName: str) -> str:
    return f'"{str(_basePath.joinpath(baseName).with_suffix(_libExt))}"'


def _getAvailableFields():
    compresibleDensity = GeneralDB.isCompressibleDensity()
    if compresibleDensity:
        fields = ['rhoU', 'rho']
    else:
        fields = ['U']

    cap = getSolverCapability(findSolver())
    if cap['usePrgh']:
        fields.append('p_rgh')
    else:
        fields.append('p')

    # Fields depending on the turbulence model
    turbulenceModel = ModelsDB.getTurbulenceModel()
    if turbulenceModel == TurbulenceModel.K_EPSILON:
        fields.append('k')
        fields.append('epsilon')
    elif turbulenceModel == TurbulenceModel.K_OMEGA:
        fields.append('k')
        fields.append('omega')
    elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
        fields.append('nuTilda')

    if ModelsDB.isEnergyModelOn():
        if compresibleDensity:
            fields.append('rhoE')
        else:
            fields.append('h')

    if ModelsDB.isMultiphaseModelOn():
        for mid, name, _, phase in coredb.CoreDB().getMaterials():
            if MaterialDB.dbTextToPhase(phase) != Phase.SOLID:
                fields.append(f'alpha.{name}')

    return fields


def getFieldValue(field) -> list:
    value = {
        'pressure': 'p',    # 'modifiedPressure': 'p_rgh',
        'speed': 'mag(U)',
        'xVelocity': 'Ux',  # Ux
        'yVelocity': 'Uy',  # Uy
        'zVelocity': 'Uz',  # Uz
        'turbulentKineticEnergy': 'k',
        'turbulentDissipationRate': 'epsilon',
        'specificDissipationRate': 'omega',
        'modifiedTurbulentViscosity': 'nuTilda',
        'temperature': 'T',
        'density': 'rho',
        'phi': 'phi',
        'material': '',
    }
    if field not in value:
        raise ValueError
    return [value[field]]


def getOperationValue(option) -> str:
    value = {
        # Surface
        'areaWeightedAverage': 'weightedAreaAverage',
        'Integral': 'areaIntegrate',
        'flowRate': 'sum',  # fields : phi
        'minimum': 'min',
        'maximum': 'max',
        'cov': 'CoV',
        # Volume
        'volumeAverage': 'volAverage',
        'volumeIntegral': 'volIntegrate',
    }
    if option not in value:
        raise ValueError
    return value[option]


def getRegionNumbers() -> dict:
    db = coredb.CoreDB()

    regionNum = {}
    regions = db.getRegions()
    for ii, dd in enumerate(regions):
        regionNum[dd] = ii
    return regionNum


class ControlDict(DictionaryFile):
    def __init__(self):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(), 'controlDict')
        self._data = None
        self._db = None

    def build(self):
        if self._data is not None:
            return self

        self._db = CoreDBReader()
        xpath = RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions'

        solvers = baramFlow.openfoam.solver.findSolvers()
        if len(solvers) != 1:  # configuration not enough yet
            solvers = ['solver']
            # raise RuntimeError

        endTime = None
        deltaT = None
        writeControl = 'runTime'
        writeInterval = None
        adjustTimeStep = 'no'
        if GeneralDB.isTimeTransient():
            endTime = self._db.getValue(xpath + '/endTime')
            timeSteppingMethod = self._db.getValue(xpath + '/timeSteppingMethod')
            writeInterval = self._db.getValue(xpath + '/reportIntervalSeconds')
            if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
                deltaT = self._db.getValue(xpath + '/timeStepSize')
            elif timeSteppingMethod == TimeSteppingMethod.ADAPTIVE.value:
                deltaT = 0.001
                writeControl = 'adjustableRunTime'
                adjustTimeStep = 'yes'
        else:
            endTime = self._db.getValue(xpath + '/numberOfIterations')
            deltaT = 1
            writeInterval = self._db.getValue(xpath + '/reportIntervalSteps')

        purgeWrite = 0
        if self._db.getValue(xpath + '/retainOnlyTheMostRecentFiles') == 'true':
            purgeWrite = self._db.getValue(xpath + '/maximumNumberOfDataFiles')

        self._data = {
            'application': solvers[0],
            'startFrom': 'latestTime',
            'startTime': 0,
            'stopAt': 'endTime',
            'endTime': endTime,
            'deltaT': deltaT,
            'writeControl': writeControl,
            'writeInterval': writeInterval,
            'purgeWrite': purgeWrite,
            'writeFormat': self._db.getValue(xpath + '/dataWriteFormat'),
            'writePrecision': self._db.getValue(xpath + '/dataWritePrecision'),
            'writeCompression': 'off',
            'timeFormat': 'general',
            'timePrecision': self._db.getValue(xpath + '/timePrecision'),
            'runTimeModifiable': 'yes',
            'adjustTimeStep': adjustTimeStep,
            'maxCo': self._db.getValue(xpath + '/maxCourantNumber'),
            'functions': self._generateResiduals()
        }

        if ModelsDB.isMultiphaseModelOn():
            self._data['maxAlphaCo'] = self._db.getValue(xpath + '/VoFMaxCourantNumber')

        if (self._db.getBoundaryConditionsByType(BoundaryType.ABL_INLET.value)
                or any(
                    [self._db.getValue(BoundaryDB.getXPath(bcid) + '/wall/velocity/type') == WallVelocityCondition.ATMOSPHERIC_WALL.value
                     for bcid, _ in self._db.getBoundaryConditionsByType(BoundaryType.WALL.value)])):
            self._data['libs'] = [_libPath('libatmosphericModels')]

        self._appendMonitoringFunctionObjects()

        return self

    def _appendMonitoringFunctionObjects(self):
        for name in self._db.getForceMonitors():
            xpath = MonitorDB.getForceMonitorXPath(name)
            patches = [BoundaryDB.getBoundaryName(bcid) for bcid in self._db.getValue(xpath + '/boundaries').split()]
            self._data['functions'][name + '_forces'] = self._generateForces(xpath, patches)
            self._data['functions'][name] = self._generateForceMonitor(xpath, patches)

        for name in self._db.getPointMonitors():
            self._data['functions'][name] = self._generatePointMonitor(MonitorDB.getPointMonitorXPath(name))

        for name in self._db.getSurfaceMonitors():
            self._data['functions'][name] = self._generateSurfaceMonitor(MonitorDB.getSurfaceMonitorXPath(name))

        for name in self._db.getVolumeMonitors():
            self._data['functions'][name] = self._generateVolumeMonitor(MonitorDB.getVolumeMonitorXPath(name))

    def _generateResiduals(self) -> dict:
        regions = self._db.getRegions()
        data = {}
        regionNum = getRegionNumbers()

        for rname in regions:   # [''] is single region.
            rgid = regionNum[rname]

            residualsName = f'solverInfo_{rgid}'

            mid = RegionDB.getMaterial(rname)
            if MaterialDB.getPhase(mid) == Phase.SOLID:
                if ModelsDB.isEnergyModelOn():
                    fields = ['h']
                else:
                    continue  # 'h' is the only property solid has
            else:
                fields = _getAvailableFields()


            data[residualsName] = {
                'type': 'solverInfo',
                'libs': [_libPath('libutilityFunctionObjects')],
                'executeControl': 'timeStep',
                'executeInterval': '1',
                'writeResidualFields': 'no',

                'fields': fields
            }
            if rname != '':
                data[residualsName].update({'region': rname})
        return data

    def _generateForces(self, xpath, patches):
        data = {
            'type': 'forces',
            'libs': [_libPath('libforces')],

            'patches': patches,
            'CofR': self._db.getVector(xpath + '/centerOfRotation'),

            'writeControl': 'timeStep',
            'writeInterval': self._db.getValue(xpath + '/writeInterval'),
            'log': 'false',
        }

        if not GeneralDB.isCompressible():
            data['p'] = 'p_rgh'  # Use "Pseudo hydrostatic pressure" for calculation

        if rname := self._db.getValue(xpath + '/region'):
            data['region'] = rname

        return data

    def _generateForceMonitor(self, xpath, patches):
        data = {
            'type': 'forceCoeffs',
            'libs': [_libPath('libforces')],

            'patches': patches,
            'rho': 'rho',
            'Aref': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/area'),
            'lRef': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/length'),
            'magUInf':  self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/velocity'),
            'rhoInf': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/density'),
            'dragDir': self._db.getVector(xpath + '/dragDirection'),
            'liftDir': self._db.getVector(xpath + '/liftDirection'),
            'CofR': self._db.getVector(xpath + '/centerOfRotation'),

            'writeControl': 'timeStep',
            'writeInterval': self._db.getValue(xpath + '/writeInterval'),
            'log': 'false',
        }

        if not GeneralDB.isCompressible():
            data['p'] = 'p_rgh'  # Use "Pseudo hydrostatic pressure" for calculation

        if rname := self._db.getValue(xpath + '/region'):
            data['region'] = rname

        return data

    def _generatePointMonitor(self, xpath):
        field = FieldHelper.DBFieldKeyToField(self._db.getValue(xpath + '/field/field'),
                                              self._db.getValue(xpath + '/field/mid'))

        if field == 'mag(U)':
            self._appendMagFieldFunctionObject()
        elif field in ('Ux', 'Uy', 'Uz'):
            self._appendComponentsFunctionObject()

        if self._db.getValue(xpath + '/snapOntoBoundary') == 'true':
            return {
                'type': 'patchProbes',
                'libs': [_libPath('libsampling')],

                'patches': [BoundaryDB.getBoundaryName(self._db.getValue(xpath + '/boundary'))],
                'fields': [field],
                'probeLocations': [self._db.getVector(xpath + '/coordinate')],

                'writeControl': 'timeStep',
                'writeInterval': self._db.getValue(xpath + '/writeInterval'),
                'log': 'false',
            }

        return {
            'type': 'probes',
            'libs': [_libPath('libsampling')],

            'fields': [field],
            'probeLocations': [self._db.getVector(xpath + '/coordinate')],

            'writeControl': 'timeStep',
            'writeInterval': self._db.getValue(xpath + '/writeInterval'),
            'log': 'false',
        }

    def _generateSurfaceMonitor(self, xpath):
        reportType = self._db.getValue(xpath + 'reportType')
        field = None
        if reportType == SurfaceReportType.MASS_FLOW_RATE.value:
            field = 'phi'
        elif reportType == SurfaceReportType.VOLUME_FLOW_RATE.value:
            field = 'U'
        else:
            field = FieldHelper.DBFieldKeyToField(self._db.getValue(xpath + '/field/field'),
                                                  self._db.getValue(xpath + '/field/mid'))

        if field == 'mag(U)':
            self._appendMagFieldFunctionObject()
        elif field in ('Ux', 'Uy', 'Uz'):
            self._appendComponentsFunctionObject()

        surface = self._db.getValue(xpath + '/surface')

        data = {
            'type': 'surfaceFieldValue',
            'libs': [_libPath('libfieldFunctionObjects')],

            'regionType': 'patch',
            'name': BoundaryDB.getBoundaryName(surface),
            'surfaceFormat': 'none',
            'fields': [field],
            'operation': SURFACE_MONITOR_OPERATION[reportType],

            'writeFields': 'false',
            'executeControl': 'timeStep',
            'executeInterval': 1,

            'writeControl': 'timeStep',
            'writeInterval': self._db.getValue(xpath + '/writeInterval'),
            'log': 'false',
        }

        if reportType == SurfaceReportType.MASS_WEIGHTED_AVERAGE.value:
            data['weightField'] = 'phi'

        if rname := BoundaryDB.getBoundaryRegion(surface):
            data['region'] = rname

        return data

    def _generateVolumeMonitor(self, xpath):
        field = FieldHelper.DBFieldKeyToField(self._db.getValue(xpath + '/field/field'),
                                              self._db.getValue(xpath + '/field/mid'))

        if field == 'mag(U)':
            self._appendMagFieldFunctionObject()
        elif field in ('Ux', 'Uy', 'Uz'):
            self._appendComponentsFunctionObject()

        data = {
            'type': 'volFieldValue',
            'libs': [_libPath('libfieldFunctionObjects')],

            'fields': [field],
            'operation': VOLUME_MONITOR_OPERATION[self._db.getValue(xpath + '/reportType')],
            'writeFields': 'false',

            'writeControl': 'timeStep',
            'writeInterval': '1',
            'log': 'false',
        }

        volume = self._db.getValue(xpath + '/volume')
        name = CellZoneDB.getCellZoneName(volume)
        if name == CellZoneDB.NAME_FOR_REGION:
            data['regionType'] = 'all'
        else:
            data['regionType'] = 'cellZone'
            data['name'] = name

        if rname := CellZoneDB.getCellZoneRegion(volume):
            data['region'] = rname

        return data

    def _appendMagFieldFunctionObject(self):
        if 'mag1' not in self._data['functions']:
            self._data['functions']['mag1'] = {
                'type':            'mag',
                'libs':            [_libPath('libfieldFunctionObjects')],

                'field':           '"U"',

                'enabled':         'true',
                'log':             'false',
                'executeControl':  'timeStep',
                'executeInterval': 1,
                'writeControl':    'none'
            }

    def _appendComponentsFunctionObject(self):
        if 'components1' not in self._data['functions']:
            self._data['functions']['components1'] = {
                'type':            'components',
                'libs':            [_libPath('libfieldFunctionObjects')],

                'field':           '"U"',

                'enabled':         'true',
                'log':             'false',
                'executeControl':  'timeStep',
                'executeInterval': 1,
                'writeControl':    'none'
            }
