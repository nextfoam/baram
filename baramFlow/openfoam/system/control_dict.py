#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import platform

from libbaram.app_path import APP_PATH
from libbaram.math import calucateDirectionsByRotation
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

import baramFlow.openfoam.solver
from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, WallVelocityCondition, DirectionSpecificationMethod
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB, Phase, MaterialType
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel, TurbulenceModelsDB
from baramFlow.coredb.scalar_model_db import ScalarSpecificationMethod, UserDefinedScalarsDB
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, SurfaceReportType, VolumeReportType, Field
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.mesh.vtk_loader import isPointInDataSet
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import findSolver, getSolverCapability
from .fv_options import generateSourceTermField, generateFixedValueField


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
    rasModel = TurbulenceModelsDB.getRASModel()
    if rasModel == TurbulenceModel.K_EPSILON or TurbulenceModelsDB.isLESKEqnModel():
        fields.append('k')
        fields.append('epsilon')
    elif rasModel == TurbulenceModel.K_OMEGA:
        fields.append('k')
        fields.append('omega')
    elif rasModel == TurbulenceModel.SPALART_ALLMARAS:
        fields.append('nuTilda')

    if ModelsDB.isEnergyModelOn():
        if compresibleDensity:
            fields.append('rhoE')
        else:
            fields.append('h')

    db = coredb.CoreDB()
    if ModelsDB.isMultiphaseModelOn():
        for mid, name, _, phase in db.getMaterials():
            if phase != Phase.SOLID.value:
                fields.append(f'alpha.{name}')
    elif ModelsDB.isSpeciesModelOn():
        for mixture, name in RegionDB.getMixturesInRegions():
            for name in MaterialDB.getSpecies(mixture).values():
                fields.append(name)

    for _, fieldName in CoreDBReader().getUserDefinedScalars():
        fields.append(fieldName)

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
        self._writeControl = 'runTime'
        self._writeInterval = None

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
        adjustTimeStep = 'no'
        if GeneralDB.isTimeTransient():
            endTime = self._db.getValue(xpath + '/endTime')
            timeSteppingMethod = self._db.getValue(xpath + '/timeSteppingMethod')
            self._writeInterval = self._db.getValue(xpath + '/reportIntervalSeconds')
            if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
                deltaT = self._db.getValue(xpath + '/timeStepSize')
            elif timeSteppingMethod == TimeSteppingMethod.ADAPTIVE.value:
                deltaT = 0.001
                self._writeControl = 'adjustableRunTime'
                adjustTimeStep = 'yes'
        else:
            endTime = self._db.getValue(xpath + '/numberOfIterations')
            deltaT = 1
            self._writeInterval = self._db.getValue(xpath + '/reportIntervalSteps')

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
            'writeControl': self._writeControl,
            'writeInterval': self._writeInterval,
            'purgeWrite': purgeWrite,
            'writeFormat': self._db.getValue(xpath + '/dataWriteFormat'),
            'writePrecision': self._db.getValue(xpath + '/dataWritePrecision'),
            'writeCompression': 'off',
            'writeAtEnd': 'true',
            'timeFormat': 'general',
            'timePrecision': self._db.getValue(xpath + '/timePrecision'),
            'runTimeModifiable': 'yes',
            'adjustTimeStep': adjustTimeStep,
            'maxCo': self._db.getValue(xpath + '/maxCourantNumber'),
            'functions': {}
        }

        if ModelsDB.isMultiphaseModelOn():
            self._data['maxAlphaCo'] = self._db.getValue(xpath + '/VoFMaxCourantNumber')

        if (self._db.getBoundaryConditionsByType(BoundaryType.ABL_INLET.value)
                or any(
                    [self._db.getValue(BoundaryDB.getXPath(bcid) + '/wall/velocity/type') == WallVelocityCondition.ATMOSPHERIC_WALL.value
                     for bcid, _ in self._db.getBoundaryConditionsByType(BoundaryType.WALL.value)])):
            self._data['libs'] = [_libPath('libatmosphericModels')]

        # calling order is important for these three function objects
        # scalar transport FO should be called first so that monitoring and residual can refer the scalar fields

        if self._db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/UDS'):
            self._appendScalarTransportFunctionObjects()

        self._appendMonitoringFunctionObjects()

        self._appendResidualFunctionObjects()

        return self

    def _appendScalarTransportFunctionObjects(self):
        for scalarID, fieldName in self._db.getUserDefinedScalars():
            fvOptions = {}
            for rname in self._db.getRegions():
                for czid, czname in self._db.getCellZones(rname):
                    fullName = f'{rname}_{czname}' if rname else czname

                    sourceTermXPath = f'{CellZoneDB.getXPath(czid)}/sourceTerms/userDefinedScalars/scalarSource[scalarID="{scalarID}"]'
                    if self._db.getAttribute(sourceTermXPath, 'disabled') == 'false':
                        fvOptions[f'scalarSource_{fullName}_{fieldName}'] = generateSourceTermField(
                            czname, sourceTermXPath, fieldName)

                    fixedValueXPath = f'{CellZoneDB.getXPath(czid)}/fixedValues/userDefinedScalars/scalar[scalarID="{scalarID}"]/value'
                    if self._db.getAttribute(fixedValueXPath, 'disabled') == 'false':
                        fvOptions[f'fixedValue_{fullName}_{fieldName}'] = generateFixedValueField(
                            czname, fixedValueXPath, fieldName)

            self._data['functions'][fieldName] = {
                'type': 'scalarTransport',
                'libs': [_libPath('libsolverFunctionObjects')],
                'field': fieldName,
                'schemesField': 'scalar',
                'nCorr': 2,
                'writeControl': self._writeControl,
                'writeInterval': self._writeInterval,
            }

            if fvOptions:
                self._data['functions'][fieldName]['fvOptions'] = fvOptions

            xpath = UserDefinedScalarsDB.getXPath(scalarID)
            specificationMethod = self._db.getValue(xpath + '/diffusivity/specificationMethod')
            if specificationMethod == ScalarSpecificationMethod.CONSTANT.value:
                self._data['functions'][fieldName]['D'] = self._db.getValue(xpath + '/diffusivity/constant')
            elif specificationMethod == ScalarSpecificationMethod.TURBULENT_VISCOSITY.value:
                self._data['functions'][fieldName]['nut'] = 'nut'
            elif specificationMethod == ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY.value:
                self._data['functions'][fieldName]['alphaD'] = self._db.getValue(
                    xpath + '/diffusivity/laminarAndTurbulentViscosity/laminarViscosityCoefficient')
                self._data['functions'][fieldName]['alphaDt'] = self._db.getValue(
                    xpath + '/diffusivity/laminarAndTurbulentViscosity/turbulentViscosityCoefficient')

            if region := self._db.getValue(xpath + '/region'):
                self._data['functions'][fieldName]['region'] = region

            if mid := int(self._db.getValue(xpath + 'material')):
                self._data['functions'][fieldName]['phase'] = MaterialDB.getName(mid)

    def _appendMonitoringFunctionObjects(self):
        for name in self._db.getForceMonitors():
            xpath = MonitorDB.getForceMonitorXPath(name)
            patches = [BoundaryDB.getBoundaryName(bcid) for bcid in self._db.getValue(xpath + '/boundaries').split()]
            self._data['functions'][name + '_forces'] = self._generateForces(xpath, patches)
            self._data['functions'][name] = self._generateForceMonitor(xpath, patches)

        for name in self._db.getPointMonitors():
            if monitorFunction := self._generatePointMonitor(MonitorDB.getPointMonitorXPath(name)):
                self._data['functions'][name] = monitorFunction

        for name in self._db.getSurfaceMonitors():
            if monitorFunction := self._generateSurfaceMonitor(MonitorDB.getSurfaceMonitorXPath(name)):
                self._data['functions'][name] = monitorFunction

        for name in self._db.getVolumeMonitors():
            if monitorFunction := self._generateVolumeMonitor(MonitorDB.getVolumeMonitorXPath(name)):
                self._data['functions'][name] = monitorFunction

    def _appendResidualFunctionObjects(self):
        regions = self._db.getRegions()
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

            self._data['functions'][residualsName] = {
                'type': 'solverInfo',
                'libs': [_libPath('libutilityFunctionObjects')],
                'executeControl': 'timeStep',
                'executeInterval': '1',
                'writeResidualFields': 'no',

                'fields': fields
            }
            if rname != '':
                self._data['functions'][residualsName].update({'region': rname})

    def _generateForces(self, xpath, patches):
        data = {
            'type': 'forces',
            'libs': [_libPath('libforces')],

            'patches': patches,
            'CofR': self._db.getVector(xpath + '/centerOfRotation'),

            'writeControl': 'timeStep',
            'writeInterval': self._db.getValue(xpath + '/writeInterval'),
            'updateHeader': 'false',
            'log': 'false',
        }

        if rname := self._db.getValue(xpath + '/region'):
            data['region'] = rname

        return data

    def _generateForceMonitor(self, xpath, patches):
        drag = self._db.getVector(xpath + '/forceDirection/dragDirection')
        lift = self._db.getVector(xpath + '/forceDirection/liftDirection')
        if self._db.getValue(xpath + '/forceDirection/specificationMethod') == DirectionSpecificationMethod.AOA_AOS.value:
            drag, lift = calucateDirectionsByRotation(
                drag, lift,
                float(self._db.getValue(xpath + '/forceDirection/angleOfAttack')),
                float(self._db.getValue(xpath + '/forceDirection/angleOfSideslip')))

        data = {
            'type': 'forceCoeffs',
            'libs': [_libPath('libforces')],

            'patches': patches,
            'rho': 'rho',
            'Aref': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/area'),
            'lRef': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/length'),
            'magUInf':  self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/velocity'),
            'rhoInf': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/density'),
            'dragDir': drag,
            'liftDir': lift,
            'CofR': self._db.getVector(xpath + '/centerOfRotation'),

            'writeControl': 'timeStep',
            'writeInterval': self._db.getValue(xpath + '/writeInterval'),
            'updateHeader': 'false',
            'log': 'false',
        }

        if not GeneralDB.isDensityBased():
            referencePressure = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'))
            operatingPressure = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
            data['pRef'] = referencePressure + operatingPressure

        if rname := self._db.getValue(xpath + '/region'):
            data['region'] = rname

        return data

    def _generatePointMonitor(self, xpath):
        coordinate = self._db.getVector(xpath + '/coordinate')
        region = self._db.getValue(xpath + '/region')

        if self._db.getValue(xpath + '/snapOntoBoundary') == 'true':
            field = self._getMonitorField(xpath, region)
            if not field:
                return None

            data = {
                'type': 'patchProbes',
                'libs': [_libPath('libsampling')],

                'patches': [BoundaryDB.getBoundaryName(self._db.getValue(xpath + '/boundary'))],
                'fields': [field],
                'probeLocations': [coordinate],

                'writeControl': 'timeStep',
                'writeInterval': self._db.getValue(xpath + '/writeInterval'),
                'updateHeader': 'false',
                'log': 'false',
            }
        else:
            if not region:
                regions = self._db.getRegions()
                if len(regions) > 1:
                    for rname in regions:
                        if isPointInDataSet(coordinate, app.internalMeshActor(rname).dataSet):
                            self._db.setValue(xpath + '/region', rname)
                            region = rname
                            break

            field = self._getMonitorField(xpath, region)
            if not field:
                return None

            data = {
                'type': 'probes',
                'libs': [_libPath('libsampling')],

                'fields': [field],
                'probeLocations': [self._db.getVector(xpath + '/coordinate')],

                'writeControl': 'timeStep',
                'writeInterval': self._db.getValue(xpath + '/writeInterval'),
                'updateHeader': 'false',
                'log': 'false',
            }

        if region:
            data['region'] = region

        return data

    def _generateSurfaceMonitor(self, xpath):
        reportType = self._db.getValue(xpath + 'reportType')
        surface = self._db.getValue(xpath + '/surface')

        region = BoundaryDB.getBoundaryRegion(surface)

        field = None
        if reportType == SurfaceReportType.MASS_FLOW_RATE.value:
            field = 'phi'
        elif reportType == SurfaceReportType.VOLUME_FLOW_RATE.value:
            field = 'U'
        else:
            field = self._getMonitorField(xpath, region)

        if not field:
            return None

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
            'updateHeader': 'false',
            'log': 'false',
        }

        if reportType == SurfaceReportType.MASS_WEIGHTED_AVERAGE.value:
            data['weightField'] = 'phi'

        if region:
            data['region'] = region

        return data

    def _generateVolumeMonitor(self, xpath):
        volume = self._db.getValue(xpath + '/volume')

        region = CellZoneDB.getCellZoneRegion(volume)
        field = self._getMonitorField(xpath, region)
        if not field:
            return None

        data = {
            'type': 'volFieldValue',
            'libs': [_libPath('libfieldFunctionObjects')],

            'fields': [field],
            'operation': VOLUME_MONITOR_OPERATION[self._db.getValue(xpath + '/reportType')],
            'writeFields': 'false',

            'writeControl': 'timeStep',
            'writeInterval': '1',
            'updateHeader': 'false',
            'log': 'false',
        }

        name = CellZoneDB.getCellZoneName(volume)
        if name == CellZoneDB.NAME_FOR_REGION:
            data['regionType'] = 'all'
        else:
            data['regionType'] = 'cellZone'
            data['name'] = name

        if region:
            data['region'] = region

        return data

    def _getMonitorField(self, xpath, rname):
        fieldType = Field(self._db.getValue(xpath + '/field/field'))
        fieldID = self._db.getValue(xpath + '/field/fieldID')

        primary = RegionDB.getMaterial(rname)
        if fieldType == Field.MATERIAL:
            if MaterialDB.getType(fieldID) == MaterialType.SPECIE:
                if fieldID not in MaterialDB.getSpecies(primary):
                    return None
            elif fieldID != primary and fieldID not in RegionDB.getSecondaryMaterials(rname):
                return None

        field = FieldHelper.DBFieldKeyToField(fieldType, fieldID)
        if field == 'mag(U)':
            self._appendMagFieldFunctionObject()
        elif field in ('Ux', 'Uy', 'Uz'):
            self._appendComponentsFunctionObject()

        return field

    def _appendMagFieldFunctionObject(self):
        if 'mag1' not in self._data['functions']:
            self._data['functions']['mag1'] = {
                'type':            'mag',
                'libs':            [_libPath('libfieldFunctionObjects')],

                'field':           '"U"',

                'enabled':         'true',
                'updateHeader':    'false',
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
                'updateHeader':    'false',
                'log':             'false',
                'executeControl':  'timeStep',
                'executeInterval': 1,
                'writeControl':    'none'
            }
