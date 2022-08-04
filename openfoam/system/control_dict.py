#!/usr/bin/env python
# -*- coding: utf-8 -*-

import openfoam.solver
from coredb import coredb
from coredb.general_db import GeneralDB
from coredb.monitor_db import MonitorDB
from coredb.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from openfoam.dictionary_file import DictionaryFile


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
        data = self._generateResiduals()

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

        fields = ['U', 'p']
        region = ''     # Get current region

        data = {
            'solverInfo': {
                'type': 'solverInfo',
                'region': region,
                'libs': ['"libutilityFunctionObjects.so"'],
                'fields': fields,
                'writeResidualFields': 'yes'
            }
        }
        return data

    def _generateForces(self, forces):
        db = coredb.CoreDB()
        data = {}

        for d in forces:
            xpath = MonitorDB.getForceMonitorXPath(d)

            name = db.getValue(xpath + '/name')  # same with b
            referenceArea = db.getValue(xpath + '/referenceArea')
            referenceLength = db.getValue(xpath + '/referenceLength')
            referenceVelocity = db.getValue(xpath + '/referenceVelocity')
            referenceDensity = db.getValue(xpath + '/referenceDensity')
            dragDirection = db.getVector(xpath + '/dragDirection')
            liftDirection = db.getVector(xpath + '/liftDirection')
            pitchAxisDirection = db.getVector(xpath + '/pitchAxisDirection')
            centerOfRotation = db.getVector(xpath + '/centerOfRotation')
            boundaries = db.getValue(xpath + '/boundaries')

            data[f'forces_{name}'] = {
                'type': 'forces',
                'libs': ['"libforces.so"'],

                'rhoInf': referenceDensity,
                'CofR': centerOfRotation,
                'liftDir': liftDirection,
                'dragDir': dragDirection,
                'pitchAxis': pitchAxisDirection,
                'magUInf': referenceVelocity,
                'lRef': referenceLength,
                'Aref': referenceArea,
                'patches': [boundaries]
            }
        return data

    def _generatePoints(self, points) -> dict:
        db = coredb.CoreDB()
        data = {}

        for d in points:
            xpath = MonitorDB.getPointMonitorXPath(d)

            name = db.getValue(xpath + '/name')
            field = db.getValue(xpath + '/field/field')
            mid = db.getValue(xpath + '/field/mid')
            interval = db.getValue(xpath + '/interval')
            coordinate = db.getVector(xpath + '/coordinate')
            snapOntoBoundary = db.getVector(xpath + '/snapOntoBoundary')

            patches = []
            data[f'probes_{name}'] = {
                'type': 'probes',
                'libs': ['"libprobes.so"'],
            }
        return data

    def _generateSurfaces(self, surfaces) -> dict:
        db = coredb.CoreDB()
        data = {}

        for d in surfaces:
            xpath = MonitorDB.getSurfaceMonitorXPath(d)

            name = db.getValue(xpath + '/name')
            reportType = db.getValue(xpath + '/reportType')
            field = db.getValue(xpath + '/field/field')
            mid = db.getValue(xpath + '/field/mid')
            surfaces = db.getValue(xpath + '/surfaces')

            data[f'surfaces_{name}'] = {
                'type': 'surfaces',
                'libs': ['"libsurfaces.so"'],

            }
        return data

    def _generateVolumes(self, volumes) -> dict:
        db = coredb.CoreDB()
        data = {}

        for d in volumes:
            xpath = MonitorDB.getVolumeMonitorXPath(d)

            name = db.getValue(xpath + '/name')
            reportType = db.getValue(xpath + '/reportType')
            field = db.getValue(xpath + '/field/field')
            mid = db.getValue(xpath + '/field/mid')
            volumes = db.getValue(xpath + '/volumes')

            data[f'volumes_{name}'] = {
                'type': 'volumes',
                'libs': ['"libvolumes.so"'],
                'fields': [field],

            }
        return data
