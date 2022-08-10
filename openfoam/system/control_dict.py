#!/usr/bin/env python
# -*- coding: utf-8 -*-

import openfoam.solver
from coredb import coredb
from coredb.general_db import GeneralDB
from coredb.boundary_db import BoundaryDB
from coredb.monitor_db import MonitorDB
from coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from openfoam.dictionary_file import DictionaryFile


def getFieldValue(field):
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

def getOperationValue(option):
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

class ControlDict(DictionaryFile):
    def __init__(self):
        super().__init__(self.systemLocation(), 'controlDict')
        self._data = None

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()
        xpath = RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions'

        solvers = openfoam.solver.findSolvers()
        if len(solvers) != 1:  # configuration not enough yet
            solvers = ['solver']
            # raise RuntimeError

        endTime = None
        deltaT = None
        writeControl = 'runTime'
        writeInterval = None
        adjustTimeStep = 'no'
        if GeneralDB.isTimeTransient():
            endTime = db.getValue(xpath + '/endTime')
            timeSteppingMethod = db.getValue(xpath + '/timeSteppingMethod')
            writeInterval = db.getValue(xpath + '/reportIntervalSeconds')
            if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
                deltaT = db.getValue(xpath + '/timeStepSize')
            elif timeSteppingMethod == TimeSteppingMethod.ADAPTIVE.value:
                deltaT = 0.001
                writeControl = 'adjustableRunTime'
                adjustTimeStep = 'yes'
        else:
            endTime = db.getValue(xpath + '/numberOfIterations')
            deltaT = 1
            writeInterval = db.getValue(xpath + '/reportIntervalSteps')

        purgeWrite = 0
        if db.getValue(xpath + '/retainOnlyTheMostRecentFiles') == 'true':
            purgeWrite = db.getValue(xpath + '/maximumNumberOfDataFiles')

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
            'writeFormat': db.getValue(xpath + '/dataWriteFormat'),
            'writePrecision': db.getValue(xpath + '/dataWritePrecision'),
            'writeCompression': 'off',
            'timeFormat': 'general',
            'timePrecision': db.getValue(xpath + '/timePrecision'),
            'runTimeModifiable': 'yes',
            'adjustTimeStep': adjustTimeStep,
            'maxCo': db.getValue(xpath + '/maxCourantNumber'),
            'functions': self._generateFunctionObjects()
        }

        return self

    def _generateFunctionObjects(self):
        db = coredb.CoreDB()
        data = {}

        data.update(self._generateResiduals())

        forces = db.getForceMonitors()
        data.update(self._generateForces(forces))

        points = db.getPointMonitors()
        data.update(self._generatePoints(points))

        surfaces = db.getSurfaceMonitors()
        data.update(self._generateSurfaces(surfaces))

        volumes = db.getVolumeMonitors()
        data.update(self._generateVolumes(volumes))

        return data

    def _generateResiduals(self) -> dict:
        db = coredb.CoreDB()
        regions = db.getRegions()
        fields = ['U', 'p']
        # 'laminar': ['U', 'p_rgh', 'h']
        # 'kOmegaSST': ['U', 'p_rgh', 'h', 'k', 'omega']
        # else: ['U', 'p_rgh', 'h', 'k', 'epsilon']

        data = {}
        for rname in regions:   # [''] is single region.
            residualsName = 'solverInfo' if rname == '' else f'solverInfo_{rname}'
            data[residualsName] = {
                'type': 'solverInfo',
                'libs': ['"libutilityFunctionObjects.so"'],
                'writeControl': 'timeStep',
                'writeInterval': '1',
                'writeResidualFields': 'yes',
                'log': 'true',

                'fields': fields
            }
            if rname != '':
                data[residualsName].update({'region': rname})
        return data

    def _generateForces(self, forces) -> dict:
        db = coredb.CoreDB()
        data = {}

        regionNum = {}
        regions = db.getRegions()
        for ii, dd in enumerate(regions):
            regionNum[dd] = ii

        for d in forces:
            xpath = MonitorDB.getForceMonitorXPath(d)
            name = db.getValue(xpath + '/name')
            boundaryIDs = db.getValue(xpath + '/boundaries')

            for bid in boundaryIDs.split() if boundaryIDs else []:
                rname = BoundaryDB.getBoundaryRegion(bid)
                patch = BoundaryDB.getBoundaryName(bid)

                regionID = regionNum[rname]
                forcesName = f'forces_{regionID}'  # f'forces_{regionNum[rname]}' : f-string: unmatched '['
                if forcesName not in data:
                    referenceArea = db.getValue(xpath + '/referenceArea')
                    referenceLength = db.getValue(xpath + '/referenceLength')
                    referenceVelocity = db.getValue(xpath + '/referenceVelocity')
                    referenceDensity = db.getValue(xpath + '/referenceDensity')
                    dragDirection = db.getVector(xpath + '/dragDirection')
                    liftDirection = db.getVector(xpath + '/liftDirection')
                    pitchAxisDirection = db.getVector(xpath + '/pitchAxisDirection')
                    centerOfRotation = db.getVector(xpath + '/centerOfRotation')

                    data[forcesName] = {
                        'type': 'forces',
                        'libs': ['"libforces.so"'],

                        'patches': [],
                        'Aref': referenceArea,
                        'lRef': referenceLength,
                        'magUInf': referenceVelocity,
                        'rhoInf': referenceDensity,
                        'dragDir': dragDirection,
                        'liftDir': liftDirection,
                        'pitchAxis': pitchAxisDirection,
                        'CofR': centerOfRotation,

                        # 'writeFields': 'yes',
                        'writeControl': 'timeStep',
                        'writeInterval': '1',
                        'log': 'true',
                    }
                data[forcesName]['patches'].append(patch)
                if rname != '':
                    data[forcesName].update({'region': rname})
        return data

    def _generatePoints(self, points) -> dict:
        db = coredb.CoreDB()
        data = {}

        regionNum = {}
        regions = db.getRegions()
        for ii, dd in enumerate(regions):
            regionNum[dd] = ii

        for d in points:
            xpath = MonitorDB.getPointMonitorXPath(d)
            name = db.getValue(xpath + '/name')
            fields = getFieldValue(db.getValue(xpath + '/field/field'))
            mid = db.getValue(xpath + '/field/mid')
            interval = db.getValue(xpath + '/interval')
            coordinate = db.getVector(xpath + '/coordinate')
            snapOntoBoundary = db.getValue(xpath + '/snapOntoBoundary')
            if snapOntoBoundary == 'true':
                pass

            bid = db.getValue(xpath + '/boundary')
            rname = BoundaryDB.getBoundaryRegion(bid)
            patch = BoundaryDB.getBoundaryName(bid)

            regionID = regionNum[rname]
            pointsName = f'points_{regionID}'
            data[pointsName] = {
                'type': 'patchProbes',
                'libs': ['"libfieldFunctionObjects.so"'],

                'patches': [],
                'writeFields': 'yes',
                'fields': fields,
                'probeLocations': [coordinate],

                'writeControl': 'timeStep',
                'writeInterval': interval,
                'log': 'true',
            }
            data[pointsName].update({'patches': patch})
            if rname != '':
                data[pointsName].update({'region': rname})
        return data

    def _generateSurfaces(self, surfaces) -> dict:
        db = coredb.CoreDB()
        data = {}

        regionNum = {}
        regions = db.getRegions()
        for ii, dd in enumerate(regions):
            regionNum[dd] = ii

        for d in surfaces:
            xpath = MonitorDB.getSurfaceMonitorXPath(d)
            name = db.getValue(xpath + '/name')
            boundaryIDs = db.getValue(xpath + '/surfaces')
            for bid in boundaryIDs.split() if boundaryIDs else []:
                rname = BoundaryDB.getBoundaryRegion(bid)
                patch = BoundaryDB.getBoundaryName(bid)

                regionID = regionNum[rname]
                surfacesName = f'surfaces_{regionID}'
                if surfacesName not in data:
                    reportType = getOperationValue(db.getValue(xpath + '/reportType'))
                    fields = getFieldValue(db.getValue(xpath + '/field/field'))
                    mid = db.getValue(xpath + '/field/mid')

                    data[surfacesName] = {
                        'type': 'surfaceFieldValue',
                        'libs': ['"libfieldFunctionObjects.so"'],

                        'regionType': 'patch',
                        'name': [],     # 개별로 생성할 것
                        'surfaceFormat': 'none',    # Need to add

                        'writeFields': 'yes',
                        'fields': fields,
                        'operation': reportType,

                        'writeControl': 'timeStep',
                        'writeInterval': '1',
                        'log': 'true',
                    }
                data[surfacesName]['name'].append(patch)  # 개별로 생성해야 함
                if rname != '':
                    data[surfacesName].update({'region': rname})
        return data

    def _generateVolumes(self, volumes) -> dict:
        db = coredb.CoreDB()
        data = {}

        regionNum = {}
        regions = db.getRegions()
        for ii, dd in enumerate(regions):
            regionNum[dd] = ii

        for d in volumes:
            xpath = MonitorDB.getVolumeMonitorXPath(d)
            name = db.getValue(xpath + '/name')
            boundaryIDs = db.getValue(xpath + '/volumes')
            for bid in boundaryIDs.split() if boundaryIDs else []:
                rname = BoundaryDB.getBoundaryRegion(bid)
                patch = BoundaryDB.getBoundaryName(bid)

                regionID = regionNum[rname]
                volumesName = f'volumes_{regionID}'
                if volumesName not in data:
                    reportType = getOperationValue(db.getValue(xpath + '/reportType'))
                    fields = getFieldValue(db.getValue(xpath + '/field/field'))
                    mid = db.getValue(xpath + '/field/mid')

                    data[volumesName] = {
                        'type': 'volFieldValue',
                        'libs': ['"libfieldFunctionObjects.so"'],

                        'patches': [],
                        'writeFields': 'yes',
                        'fields': fields,
                        'operation': reportType,

                        'writeControl': 'timeStep',
                        'writeInterval': '1',
                        'log': 'true',
                    }
                data[volumesName]['patches'].append(patch)
                if rname != '':
                    data[volumesName].update({'region': rname})
        return data

