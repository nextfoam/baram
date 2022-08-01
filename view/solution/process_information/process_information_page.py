#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QWidget

from coredb import coredb
from coredb.project import Project, SolverStatus
from openfoam.run import launchSolver
import openfoam.solver
from openfoam.file_system import FileSystem
from .process_information_page_ui import Ui_ProcessInformationPage


class ProcessInformationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._connectSignalsSlots()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._showStatus(Project.instance().solverStatus())

        return super().showEvent(ev)

    def save(self):
        pass

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        Project.instance().statusChanged.connect(self._update)

    def _startCalculationClicked(self):
        solvers = openfoam.solver.findSolvers()
        caseRoot = FileSystem.caseRoot()
        numCores = self._db.getValue('.//runCalculation/parallel/numberOfCores')

        solvers = ['chtMultiRegionFoam']
        caseRoot = 'D:/Data/baram/multiRegionHeater'

        Project.instance().setSolverProcess(launchSolver(solvers[0], Path(caseRoot), int(numCores)))

        self._showSolverStatusRunning()

    def _cancelCalculationClicked(self):
        #

        #
        self._showSolverStatusNone()
        self._ui.status.setText(self.tr('Canceled'))

    def _saveAndStopCalculationClicked(self):
        self._ui.cancelCalculation.hide()
        self._ui.saveAndStopCalculation.setDisabled(True)
        self._ui.updateConfiguration.setDisabled(True)

    def _updateConfigurationClicked(self):
        ...

    def _update(self):
        self._showStatus(Project.instance().solverStatus())

    def _showStatus(self, status):
        if status == SolverStatus.NONE:
            self._showSolverStatusNone()

        elif status == SolverStatus.RUNNING:
            self._showSolverStatusRunning()

        elif status == SolverStatus.WAITING:
            self._showSolverStatusWaiting()
        else:
            pass

    def _showSolverStatusNone(self):
        self._ui.id.setText(self.tr('-'))
        self._ui.created.setText(self.tr('-'))
        self._ui.status.setText(self.tr('Not Running'))

        self._ui.startCalculation.show()
        self._ui.cancelCalculation.hide()
        self._ui.saveAndStopCalculation.setDisabled(True)
        self._ui.updateConfiguration.setDisabled(True)

    def _showSolverStatusRunning(self):
        project = Project.instance()

        pid, startTime = project.solverProcess()

        self._ui.id.setText(self.tr(f'{pid}'))
        self._ui.created.setText(self.tr(f'{startTime}'))
        self._ui.status.setText(self.tr('Running'))

        self._ui.startCalculation.hide()
        self._ui.cancelCalculation.show()
        self._ui.saveAndStopCalculation.setEnabled(True)
        self._ui.updateConfiguration.setEnabled(True)

    def _showSolverStatusWaiting(self):
        ...

