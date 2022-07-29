#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import psutil, signal
import time, datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from coredb import coredb
from coredb.project import Project, SolverStatus
from openfoam.run import launchSolver
from openfoam.system.fv_solution import FvSolution
from openfoam.system.control_dict import ControlDict
from openfoam.system.fv_schemes import FvSchemes
from openfoam.system.fv_options import FvOptions
import openfoam.solver
from openfoam.file_system import FileSystem
from .process_information_page_ui import Ui_ProcessInformationPage

SOLVER_CHECK_INTERVAL = 3000

class ProcessInformationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._project = Project.instance()

        self._solvers = openfoam.solver.findSolvers()
        self._caseRoot = FileSystem.caseRoot()

        self._connectSignalsSlots()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._showStatus(self._project.solverStatus())

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        self._project.statusChanged.connect(self._update)

    def _startCalculationClicked(self):
        # CaseGenerator().generateFiles()

        numCores = self._db.getValue('.//runCalculation/parallel/numberOfCores')

        pid, createdTime = launchSolver(self._solvers[0], Path(self._caseRoot), int(numCores))

        self._project.setSolverProcess(pid, createdTime)

        self._showStatusRunning()

    def _cancelCalculationClicked(self):
        # controlDict = ControlDict().build()
        # controlDict.asDict()['stopAt'] = 'noWriteNow'
        # controlDict.write()

        from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
        conDict = ParsedParameterFile(f'{self._caseRoot}/system/controlDict')
        conDict['stopAt'] = 'noWriteNow'
        conDict.writeFile()

        self._showStatusNone()
        self._ui.status.setText(self.tr('Canceled'))

    def _saveAndStopCalculationClicked(self):
        # controlDict = ControlDict().build()
        # controlDict.asDict()['stopAt'] = 'writeNow'
        # controlDict.write()

        # from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
        # conDict = ParsedParameterFile(f'{self._caseRoot}/system/controlDict')
        # conDict['stopAt'] = 'writeNow'
        # conDict.writeFile()

        self._timer = QTimer()
        self._timer.setInterval(SOLVER_CHECK_INTERVAL)
        self._timer.timeout.connect(self._waitingStop)
        self._timer.start()

    def _waitingStop(self):
        try:
            print(self._project.pid)

            ps = psutil.Process(pid=self._project.pid)
            print(self._project.startTime, ps.create_time())

            if ps.create_time() == self._project.startTime:
                psutil.Popen.send_signal(signal.SIGTERM)
                # self._project.setStatus(SolverStatus.RUNNING)

        except psutil.NoSuchProcess:
            self._project.setStatus(SolverStatus.NONE)
            self._timer.stop()

    def _updateConfigurationClicked(self):
        regions = self._db.getRegions()
        for rname in regions:
            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()
            FvOptions(rname).build().write()
        ControlDict().build().write()

    def _update(self, status):
        self._showStatus(status)

    def _showStatus(self, status):
        if status == SolverStatus.NONE:
            self._showStatusNone()

        elif status == SolverStatus.RUNNING:
            self._showStatusRunning()

        elif status == SolverStatus.WAITING:
            self._showStatusWaiting()
        else:
            pass

    def _showStatusNone(self):
        self._ui.id.setText(self.tr('-'))
        self._ui.created.setText(self.tr('-'))
        self._ui.status.setText(self.tr('Not Running'))

        self._ui.startCalculation.show()
        self._ui.startCalculation.setEnabled(True)
        self._ui.cancelCalculation.hide()
        self._ui.saveAndStopCalculation.setDisabled(True)
        self._ui.updateConfiguration.setEnabled(True)

        # controlDict = ControlDict().build()
        # controlDict.asDict()['startFrom'] = 'latestTime'
        # controlDict.asDict()['stopAt'] = 'endTime'
        # controlDict.write()

        from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
        conDict = ParsedParameterFile(f'{self._caseRoot}/system/controlDict')
        conDict['startFrom'] = 'firstTime'  ### should be deleted
        conDict['stopAt'] = 'endTime'
        conDict.writeFile()

    def _showStatusRunning(self):

        startTime = self._project.startTime

        print(startTime)
        # print(time.localtime(startTime))
        # print(datetime.datetime.fromtimestamp(startTime))
        # print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(startTime)))

        self._ui.id.setText(self.tr(f'{self._project.pid}'))
        self._ui.created.setText(self.tr(f'{startTime}'))
        self._ui.status.setText(self.tr('Running'))

        self._ui.startCalculation.hide()
        self._ui.cancelCalculation.show()
        self._ui.cancelCalculation.setEnabled(True)
        self._ui.saveAndStopCalculation.setEnabled(True)
        self._ui.updateConfiguration.setEnabled(True)

    def _showStatusWaiting(self):
        self._ui.startCalculation.setDisabled(True)
        self._ui.cancelCalculation.setDisabled(True)
        self._ui.saveAndStopCalculation.setDisabled(True)
        self._ui.updateConfiguration.setDisabled(True)

