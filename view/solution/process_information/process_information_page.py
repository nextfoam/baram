#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QWidget

from coredb import coredb
from coredb.project import Project, SolverStatus
from openfoam.case_generator import CaseGenerator
from openfoam.run import launchSolver
from openfoam.system.fv_solution import FvSolution
from openfoam.system.control_dict import ControlDict
from openfoam.system.fv_schemes import FvSchemes
from openfoam.system.fv_options import FvOptions
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

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        Project.instance().statusChanged.connect(self._update)

    def _startCalculationClicked(self):
        CaseGenerator().generateFiles()

        solvers = openfoam.solver.findSolvers()
        caseRoot = FileSystem.caseRoot()
        numCores = self._db.getValue('.//runCalculation/parallel/numberOfCores')

        # solvers = ['chtMultiRegionFoam']
        # caseRoot = '/home/test/Desktop/TestBARAM/multiRegionHeater/'

        pid, createdTime = launchSolver(solvers[0], Path(caseRoot), int(numCores))
        Project.instance().setSolverProcess(pid, createdTime)

        self._showStatusRunning()

    def _cancelCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'noWriteNow'
        controlDict.write()

        self._showStatusNone()
        self._ui.status.setText(self.tr('Canceled'))

    def _saveAndStopCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'writeNow'
        controlDict.write()

        self._ui.cancelCalculation.hide()
        self._ui.saveAndStopCalculation.setDisabled(True)

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

    def _showStatusRunning(self):
        project = Project.instance()

        pid = project.pid
        startTime = project.startTime

        self._ui.id.setText(self.tr(f'{pid}'))
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

