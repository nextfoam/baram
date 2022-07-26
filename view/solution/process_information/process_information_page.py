#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QWidget

from coredb import coredb
from openfoam.run import launchSolver
from openfoam.file_system import FileSystem
from .process_information_page_ui import Ui_ProcessInformationPage


class ProcessInformationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)

    def _startCalculationClicked(self):
        solver = 'simpleFoam'
        caseRoot = FileSystem.caseRoot()
        numCores = self._db.getValue('.//runCalculation/parallel/numberOfCores')
        launchSolver(solver, Path(caseRoot), int(numCores))

    def _saveAndStopCalculationClicked(self):
        ...

    def _updateConfigurationClicked(self):
        ...

