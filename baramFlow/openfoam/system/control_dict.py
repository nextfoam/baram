#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.math import calucateDirectionsByRotation
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.app import app
from baramFlow.base.constants import FieldType, VectorComponent, FieldCategory
from baramFlow.base.field import HEAT_TRANSFER_COEFF, WALL_HEAT_FLUX, AGE, MACH_NUMBER, Q, TOTAL_PRESSURE, VORTICITY
from baramFlow.base.field import WALL_SHEAR_STRESS, WALL_Y_PLUS, CELSIUS_TEMPERATURE
from baramFlow.base.material.material import Phase
from baramFlow.base.monitor.monitor import getMonitorField
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, WallMotion, DirectionSpecificationMethod
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from baramFlow.coredb.scalar_model_db import ScalarSpecificationMethod, UserDefinedScalarsDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.mesh.vtk_loader import isPointInDataSet
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects.collateral_fields import foAgeMonitor, foHeatTransferCoefficientMonitor
from baramFlow.openfoam.function_objects.collateral_fields import foMachNumberMonitor, foQMonitor
from baramFlow.openfoam.function_objects.collateral_fields import foTotalPressureMonitor, foVorticityMonitor
from baramFlow.openfoam.function_objects.collateral_fields import foWallHeatFluxMonitor, foWallShearStressMonitor
from baramFlow.openfoam.function_objects.collateral_fields import foWallYPlusMonitor, foCelsiusTemperatureMonitor
from baramFlow.openfoam.function_objects.components import foComponentsMonitor
from baramFlow.openfoam.function_objects.force_coeffs import foForceCoeffsMonitor
from baramFlow.openfoam.function_objects.forces import foForcesMonitor
from baramFlow.openfoam.function_objects.mag import foMagMonitor
from baramFlow.openfoam.function_objects.patch_probes import foPatchProbesMonitor
from baramFlow.openfoam.function_objects.probes import foProbesMonitor
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType, foSurfaceFieldValueMonitor
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType, VolumeType, foVolFieldValueMonitor
from baramFlow.openfoam.solver import findSolver, usePrgh

from .fv_options import generateSourceTermField, generateFixedValueField


def _getSolverInfoFields(rname: str)->list[str]:
    db = coredb.CoreDB()

    solveFlow = db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/flow')
    solveEnergy = (db.getAttribute(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/energy', 'disabled') == 'false')
    solveUDS = db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/UDS')

    compresibleDensity = GeneralDB.isCompressibleDensity()

    mid = RegionDB.getMaterial(rname)
    phase = MaterialDB.getPhase(mid)

    fields: list[str] = []

    if solveFlow and phase != Phase.SOLID:
        if compresibleDensity:
            fields.extend(['rhoU', 'rho'])
        else:
            fields.append('U')

        if usePrgh():
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

        if ModelsDB.isMultiphaseModelOn():
            for _, name, _, phase in MaterialDB.getMaterials():
                if phase != Phase.SOLID.value:
                    fields.append(f'alpha.{name}')

        if ModelsDB.isSpeciesModelOn():
            for mixture, _ in RegionDB.getMixturesInRegions():
                for name in MaterialDB.getSpecies(mixture).values():
                    fields.append(name)

    if solveEnergy:
        if ModelsDB.isEnergyModelOn():
            if compresibleDensity:
                fields.append('rhoE')
            else:
                fields.append('h')

    if solveUDS and phase != Phase.SOLID:
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


def isAtmosphericWall(bcid):
    db = coredb.CoreDB()
    xpath = BoundaryDB.getXPath(bcid)

    return (db.getValue(xpath + '/wall/velocity/wallMotion/type') == WallMotion.STATIONARY_WALL.value
            and db.getBool(xpath + '/wall/velocity/wallMotion/stationaryWall/atmosphericWall'))


def collateralFOName(field, rname):
    return f'collateral_{field.codeName}_{rname}'


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

        endTime = None
        deltaT = None
        adjustTimeStep = 'no'
        if GeneralDB.isTimeTransient():
            endTime = self._db.getValue(xpath + '/endTime')
            timeSteppingMethod = (TimeSteppingMethod.FIXED.value if GeneralDB.isCompressibleDensity()
                                  else self._db.getValue(xpath + '/timeSteppingMethod'))
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
            'application': findSolver(),
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
            'maxDi': self._db.getValue(xpath + '/maxDiffusionNumber'),
            'functions': {}
        }

        if ModelsDB.isMultiphaseModelOn():
            self._data['maxAlphaCo'] = self._db.getValue(xpath + '/VoFMaxCourantNumber')

        if (BoundaryDB.getBoundaryConditionsByType(BoundaryType.ABL_INLET)
                or any([isAtmosphericWall(bcid)
                        for bcid, _ in BoundaryDB.getBoundaryConditionsByType(BoundaryType.WALL)])):
            self._data['libs'] = ['atmosphericModels']

        # calling order is important for these three function objects
        # scalar transport FO should be called first so that monitoring and residual can refer the scalar fields

        if self._db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/UDS'):
            self._appendScalarTransportFunctionObjects()

        self._appendCollateralFieldsFunctionObjects(
            NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/collateralFields')

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
                'libs': ['solverFunctionObjects'],
                'field': fieldName,
                'schemesField': 'scalar',
                'nCorr': '0' if not GeneralDB.isTimeTransient() else self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfCorrectors'),
                'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/momentum/absolute'),
                'writeControl': self._writeControl,
                'writeInterval': self._writeInterval,
            }

            if fvOptions:
                self._data['functions'][fieldName]['fvOptions'] = fvOptions

            xpath = UserDefinedScalarsDB.getXPath(scalarID)
            specificationMethod = self._db.getValue(xpath + '/diffusivity/specificationMethod')
            if specificationMethod == ScalarSpecificationMethod.CONSTANT.value:
                coeff = float(self._db.getValue(xpath + '/diffusivity/constant'))
                self._data['functions'][fieldName]['D'] = coeff if coeff > 0 else '1e-10'
            # elif specificationMethod == ScalarSpecificationMethod.TURBULENT_VISCOSITY.value:
            #     self._data['functions'][fieldName]['nut'] = 'nut'
            elif specificationMethod == ScalarSpecificationMethod.LAMINAR_AND_TURBULENT_VISCOSITY.value:
                coeff = float(self._db.getValue(xpath + '/diffusivity/laminarAndTurbulentViscosity/laminarViscosityCoefficient'))
                self._data['functions'][fieldName]['alphaD'] = coeff if coeff > 0 else '1e-10'
                coeff = float(self._db.getValue(xpath + '/diffusivity/laminarAndTurbulentViscosity/turbulentViscosityCoefficient'))
                self._data['functions'][fieldName]['alphaDt'] = coeff if coeff > 0 else '1e-10'

            if rname := self._db.getValue(xpath + '/region'):
                self._data['functions'][fieldName]['region'] = rname

            mid = self._db.getValue(xpath + 'material')
            if mid != '0':
                self._data['functions'][fieldName]['phase'] = 'alpha.' + MaterialDB.getName(mid)

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

            fields = _getSolverInfoFields(rname)

            if len(fields) == 0:
                continue

            self._data['functions'][residualsName] = {
                'type': 'solverInfo',
                'libs': ['utilityFunctionObjects'],
                'executeControl': 'timeStep',
                'executeInterval': '1',
                'writeResidualFields': 'no',

                'fields': fields
            }
            if rname != '':
                self._data['functions'][residualsName].update({'region': rname})

    def _appendAdditionalFO(self, monitorField, rname):
        field = monitorField.field

        if field.type == FieldType.VECTOR:
            if monitorField.component == VectorComponent.MAGNITUDE and 'mag1' not in self._data['functions']:
                self._data['functions']['mag1'] = foMagMonitor('U', rname, 1)
            elif 'components1' not in self._data['functions']:
                self._data['functions']['components1'] = foComponentsMonitor('U', rname, 1)

            return

        if field.category != FieldCategory.COLLATERAL:
            return

        foName = collateralFOName(field, rname)
        if foName in self._data['functions']:
            return

        if ModelsDB.isEnergyModelOn():
            if field == HEAT_TRANSFER_COEFF:
                plainWalls  = [bcname for _, bcname in BoundaryDB.getBoundaryConditionsByType(BoundaryType.WALL, rname)]
                thermowalls = [bcname for _, bcname in BoundaryDB.getBoundaryConditionsByType(BoundaryType.THERMO_COUPLED_WALL, rname)]
                patches = plainWalls + thermowalls
                self._data['functions'][foName] = foHeatTransferCoefficientMonitor(rname, patches, 1)
            elif field == WALL_HEAT_FLUX:
                self._data['functions'][foName] = foWallHeatFluxMonitor(rname, 1)
            elif field == CELSIUS_TEMPERATURE:
                self._data['functions'][foName] = foCelsiusTemperatureMonitor(rname, 1)

        if self._db.getRegionProperties(rname).isFluid():
            if not GeneralDB.isTimeTransient() and not GeneralDB.isDensityBased():
                if field == AGE:
                    self._data['functions'][foName] = foAgeMonitor(rname, 1)

            if ModelsDB.isEnergyModelOn() and not GeneralDB.isDensityBased():
                if field == MACH_NUMBER:
                    self._data['functions'][foName] = foMachNumberMonitor(rname, 1)

            if field == Q:
                self._data['functions'][foName] = foQMonitor(rname, 1)
            elif field == TOTAL_PRESSURE:
                self._data['functions'][foName] = foTotalPressureMonitor(rname, 1)
            elif field == VORTICITY:
                self._data['functions'][foName] = foVorticityMonitor(rname, 1)
            elif field == WALL_SHEAR_STRESS:
                self._data['functions'][foName] = foWallShearStressMonitor(rname, 1)
            elif field == WALL_Y_PLUS:
                self._data['functions'][foName] = foWallYPlusMonitor(rname, 1)

    def _generateForces(self, xpath, patches):
        cofr = self._db.getVector(xpath + '/centerOfRotation')
        rname = self._db.getValue(xpath + '/region')
        interval = int(self._db.getValue(xpath + '/writeInterval'))

        if GeneralDB.isDensityBased():
            pRef = None
        else:
            referencePressure = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'))
            operatingPressure = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
            pRef = referencePressure + operatingPressure

        data = foForcesMonitor(patches, cofr, pRef, rname, interval)

        return data

    def _generateForceMonitor(self, xpath, patches):
        aRef = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/area'))
        lRef = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/length'))
        magUInf = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/velocity'))
        rhoInf = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/density'))
        dragDir = self._db.getVector(xpath + '/forceDirection/dragDirection')
        liftDir = self._db.getVector(xpath + '/forceDirection/liftDirection')
        cofr = self._db.getVector(xpath + '/centerOfRotation')

        if self._db.getValue(xpath + '/forceDirection/specificationMethod') == DirectionSpecificationMethod.AOA_AOS.value:
            dragDir, liftDir = calucateDirectionsByRotation(
                dragDir, liftDir,
                float(self._db.getValue(xpath + '/forceDirection/angleOfAttack')),
                float(self._db.getValue(xpath + '/forceDirection/angleOfSideslip')))

        if GeneralDB.isDensityBased():
            pRef = None
        else:
            referencePressure = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'))
            operatingPressure = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
            pRef = referencePressure + operatingPressure

        rname = self._db.getValue(xpath + '/region')

        interval = int(self._db.getValue(xpath + '/writeInterval'))

        data = foForceCoeffsMonitor(patches, aRef, lRef, magUInf, rhoInf, dragDir, liftDir, cofr, pRef, rname, interval)

        return data

    def _generatePointMonitor(self, xpath):
        coordinate = self._db.getVector(xpath + '/coordinate')
        interval = int(self._db.getValue(xpath + '/writeInterval'))
        rname = self._db.getValue(xpath + '/region')
        snapOntoBoundary = self._db.getValue(xpath + '/snapOntoBoundary') == 'true'
        field = getMonitorField(xpath)


        if snapOntoBoundary:
            bcid = self._db.getValue(xpath + '/boundary')
            boundary = BoundaryDB.getBoundaryName(bcid)
            rname = BoundaryDB.getBoundaryRegion(bcid)
            data = foPatchProbesMonitor(boundary, field.openfoamField(), coordinate, rname, interval)
        else:
            if not rname:
                for name in self._db.getRegions():
                    if isPointInDataSet(coordinate, app.internalMeshActor(name).dataSet):
                        self._db.setValue(xpath + '/region', name)
                        rname = name
                        break
                else:
                    return None

            self._appendAdditionalFO(field, rname)
            data = foProbesMonitor(field.openfoamField(), coordinate, rname, interval)

        return data

    def _generateSurfaceMonitor(self, xpath):
        reportType = SurfaceReportType(self._db.getValue(xpath + 'reportType'))
        surface = self._db.getValue(xpath + '/surface')
        patchName = BoundaryDB.getBoundaryName(surface)
        rname = BoundaryDB.getBoundaryRegion(surface)
        interval = int(self._db.getValue(xpath + '/writeInterval'))
        field = getMonitorField(xpath)

        if reportType == SurfaceReportType.MASS_FLOW_RATE:
            fieldText = 'phi'
        elif reportType == SurfaceReportType.VOLUME_FLOW_RATE:
            fieldText = 'U'
        else:
            fieldText = field.openfoamField()

        self._appendAdditionalFO(field, rname)
        data = foSurfaceFieldValueMonitor(patchName, fieldText, reportType, rname, interval)

        return data

    def _generateVolumeMonitor(self, xpath):
        volume = self._db.getValue(xpath + '/volume')
        reportType = VolumeReportType(self._db.getValue(xpath + '/reportType'))
        interval = int(self._db.getValue(xpath + '/writeInterval'))
        region = CellZoneDB.getCellZoneRegion(volume)
        field = getMonitorField(xpath)

        name = CellZoneDB.getCellZoneName(volume)
        if CellZoneDB.isRegion(name):
            volumeType = VolumeType.All
            volumeName = None
        else:
            volumeType = VolumeType.CELLZONE
            volumeName = name

        self._appendAdditionalFO(field, region)
        data = foVolFieldValueMonitor(volumeType, volumeName, field.openfoamField(), reportType, region, interval)

        return data

    def _appendCollateralFieldsFunctionObjects(self, xpath):
        for rname in self._db.getRegions():

            if ModelsDB.isEnergyModelOn():
                if self._db.getBool(xpath + '/heatTransferCoefficient'):
                    plainWalls  = [bcname for _, bcname in BoundaryDB.getBoundaryConditionsByType(BoundaryType.WALL, rname)]
                    thermowalls = [bcname for _, bcname in BoundaryDB.getBoundaryConditionsByType(BoundaryType.THERMO_COUPLED_WALL, rname)]
                    patches = plainWalls + thermowalls
                    self._data['functions'][collateralFOName(HEAT_TRANSFER_COEFF, rname)] = foHeatTransferCoefficientMonitor(rname, patches, 1)
                elif self._db.getBool(xpath + '/wallHeatFlux'):
                    self._data['functions'][collateralFOName(WALL_HEAT_FLUX, rname)] = foWallHeatFluxMonitor(rname, 1)

            region = self._db.getRegionProperties(rname)

            if region.isFluid():

                if not GeneralDB.isTimeTransient() and not GeneralDB.isDensityBased():
                    if self._db.getBool(xpath + '/age'):
                        self._data['functions'][collateralFOName(AGE, rname)] = foAgeMonitor(rname, 1)

                if ModelsDB.isEnergyModelOn() and not GeneralDB.isDensityBased():
                    if self._db.getBool(xpath + '/machNumber'):
                        self._data['functions'][collateralFOName(MACH_NUMBER, rname)] = foMachNumberMonitor(rname, 1)

                if self._db.getBool(xpath + '/q'):
                    self._data['functions'][collateralFOName(Q, rname)] = foQMonitor(rname, 1)

                if self._db.getBool(xpath + '/totalPressure'):
                    self._data['functions'][collateralFOName(TOTAL_PRESSURE, rname)] = foTotalPressureMonitor(rname, 1)

                if self._db.getBool(xpath + '/vorticity'):
                    self._data['functions'][collateralFOName(VORTICITY, rname)] = foVorticityMonitor(rname, 1)

                if self._db.getBool(xpath + '/wallShearStress'):
                    self._data['functions'][collateralFOName(WALL_SHEAR_STRESS, rname)] = foWallShearStressMonitor(rname, 1)

                if self._db.getBool(xpath + '/wallYPlus'):
                    self._data['functions'][collateralFOName(WALL_Y_PLUS, rname)] = foWallYPlusMonitor(rname, 1)
