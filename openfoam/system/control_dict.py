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
        }

        return self
