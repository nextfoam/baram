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
            'functions': self._buildFunctionObjects()
        }

        return self

    def _buildFunctionObjects(self):
        db = coredb.CoreDB()
        data = self._buildResiduals()

        forces = db.getForceMonitors()
        if len(forces) > 0:
            data.update(self._buildForces(forces))

        points = db.getPointMonitors()
        if len(points) > 0:
            data.update(self._buildPoints(points))

        surfaces = db.getSurfaceMonitors()
        if len(surfaces) > 0:
            data.update(self._buildSurfaces(surfaces))

        volumes = db.getVolumeMonitors()
        if len(volumes) > 0:
            data.update(self._buildVolumes(volumes))

        return data

    def _buildResiduals(self):
        db = coredb.CoreDB()

        fields = '(U p)'

        data = {
            'solverInfo': {
                'type': 'solverInfo',
                'libs': '("libutilityFunctionObjects.so")',
                'fields': fields,
                'writeResidualFields': 'yes'
            }
        }
        return data

    def _buildForces(self, data):
        data = {}
        for i in data:
            dataName = f'forces{i}'
            patches = '()'
            data[dataName] = {
                'type': 'forces',
                'libs': '("libforces.so")',
                'patches': patches
            }
        return data
    def _buildPoints(self, data):
        data = {}
        for i in data:
            dataName = f'points{i}'
            patches = '()'
            data[dataName] = {
                'type': 'points',
                'libs': '("libpoints.so")',
                'patches': patches
            }
        return data

    def _buildSurfaces(self, data):
        data = {}
        for i in data:
            dataName = f'surfaces{i}'
            patches = '()'
            data[dataName] = {
                'type': 'surfaces',
                'libs': '("libsurfaces.so")',
                'patches': patches
            }
        return data

    def _buildVolumes(self, data):
        data = {}
        for i in data:
            dataName = f'volumes{i}'
            patches = '()'
            data[dataName] = {
                'type': 'volumes',
                'libs': '("libvolumes.so")',
                'patches': patches
            }
        return data

