#!/usr/bin/env python
# -*- coding: utf-8 -*-

import openfoam.solver
from coredb import coredb
from view.setup.general.general_db import GeneralDB
from view.solution.run_calculation.run_calculation_db import RunCalculationDB, TimeSteppingMethod
from openfoam.dictionary_file import DictionaryFile


class ControlDict(DictionaryFile):
    def __init__(self):
        super().__init__(self.systemLocation(), 'controlDict')
        self._data = None

    def build(self):
        if self._data is not None:
            return

        db = coredb.CoreDB()
        xpath = RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions'

        # ToDo: raise error when no solver is found
        solvers = openfoam.solver.findSolvers()
        if len(solvers) != 1:  # configuration not enough yet
            solvers = ['solver']
            # raise RuntimeError

        endTime = db.getValue(xpath + '/numberOfIterations')
        if GeneralDB.isTimeTransient():
            endTime = db.getValue(xpath + '/endTime')
        deltaT = None
        writeControl = None
        timeSteppingMethod = db.getValue(xpath + '/timeSteppingMethod')
        if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
            deltaT = db.getValue(xpath + '/timeStepSize'),
            writeControl = 'runTime'
        elif timeSteppingMethod == TimeSteppingMethod.ADAPTIVE.value:
            deltaT = 0.001
            writeControl = 'adjustableRunTime'

        writeInterval = db.getValue(xpath + '/reportIntervalSteps')
        if GeneralDB.isTimeTransient():
            writeInterval = db.getValue(xpath + '/reportIntervalSeconds')

        purgeWrite = 0
        if db.getValue(xpath + '/retainOnlyTheMostRecentFiles') == 'true':
            purgeWrite = db.getValue(xpath + '/retainOnlyTheMostRecentFiles')

        self._data = {
            'application': solvers[0],
            'startFrom': 'latestTime',
            'startTime': 0,
            'stopAt': 'endTime',
            'endTime': endTime,
            # ToDo: adaptive일 때는 0.001
            'deltaT': deltaT,
            'writeControl': timeSteppingMethod,
            'writeInterval': writeInterval,
            'purgeWrite': purgeWrite,
            'writeFormat': db.getValue(xpath + '/dataWriteFormat'),
            'writePrecision': db.getValue(xpath + '/dataWritePrecision'),
            'writeCompression': 'off',
            'timeFormat': 'general',
            'timePrecision': db.getValue(xpath + '/timePrecision'),
            'runTimeModifiable': 'yes',
            'adjustTimeStep': 'no',
            # 'maxCo': db.getValue(xpath + '/'),     # ToDo: maxCo
        }

        return self
