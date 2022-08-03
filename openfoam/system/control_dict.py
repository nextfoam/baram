#!/usr/bin/env python
# -*- coding: utf-8 -*-

import openfoam.solver
from coredb import coredb
from coredb.general_db import GeneralDB
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

    def _generateResiduals(self):
        db = coredb.CoreDB()

        fields = '(U p)'

        data = {
            'solverInfo': {
                'type': 'solverInfo',
                # 'region': '',
                'libs': ['"libutilityFunctionObjects.so"'],
                'fields': fields,
                'writeResidualFields': 'yes'
            }
        }
        return data

    def _generateForces(self, forces):
        data = {}
        for d in forces:
            dataName = f'forces_{d}'
            patches = []
            data[dataName] = {
                'type': 'forces',
                'libs': ['"libforces.so"'],
                'patches': patches
            }
        return data

    def _generatePoints(self, points):
        data = {}
        for d in points:
            dataName = f'points_{d}'
            patches = []
            data[dataName] = {
                'type': 'points',
                'libs': ['"libpoints.so"'],
                'patches': patches
            }
        return data

    def _generateSurfaces(self, surfaces):
        data = {}
        for d in surfaces:
            dataName = f'surfaces_{d}'
            patches = []
            data[dataName] = {
                'type': 'surfaces',
                'libs': ['"libsurfaces.so"'],
                'patches': patches
            }
        return data

    def _generateVolumes(self, volumes):
        data = {}
        for d in volumes:
            dataName = f'volumes_{d}'
            patches = []
            data[dataName] = {
                'type': 'volumes',
                'libs': ['"libvolumes.so"'],
                'patches': patches
            }
        return data

