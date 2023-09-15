#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog, QMessageBox

from baram.coredb import coredb
from baram.coredb.app_settings import AppSettings
from baram.coredb.run_calculation_db import RunCalculationDB
from baram.openfoam import parallel
from baram.openfoam.parallel import ParallelType
from baram.openfoam.redistribution_task import RedistributionTask
from baram.view.widgets.progress_dialog_simple import ProgressDialogSimple
from .edit_hostfile_dialog import EditHostfileDialog
from .parallel_environment_dialog_ui import Ui_parallelEnvironmentDialog


def _getStackIndex(ptype: ParallelType):
    if ptype == ParallelType.LOCAL_MACHINE:
        return 0
    elif ptype == ParallelType.CLUSTER:
        return 1
    elif ptype == ParallelType.SLURM:
        return 2
    else:
        raise AssertionError


class ParallelEnvironmentDialog(QDialog):
    def __init__(self, parent):
        """Constructs parallel environment dialog.
        """
        super().__init__(parent)

        self._parent = parent

        self._xpath = RunCalculationDB.RUN_CALCULATION_XPATH

        self._ui = Ui_parallelEnvironmentDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.editHostFile.clicked.connect(self._editHostFileClicked)

        self._ui.typeLocalMachine.toggled.connect(self._typeLocalMachineToggled)
        self._ui.typeCluster.toggled.connect(self._typeClusterToggled)

        self._ui.applyButton.clicked.connect(self.apply)
        self._ui.closeButton.clicked.connect(self.close)

    @qasync.asyncSlot()
    async def apply(self):
        try:
            numCores = int(self._ui.numberOfCores.text())
        except ValueError:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr('Error in Number of Cores'))
            return

        if numCores <= 0:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr('Number of Cores should be greater than 0'))
            return

        if self._ui.typeLocalMachine.isChecked():
            pType = ParallelType.LOCAL_MACHINE
        elif self._ui.typeCluster.isChecked():
            pType = ParallelType.CLUSTER
        elif self._ui.typeSlurm.isChecked():
            pType = ParallelType.SLURM
        else:
            raise RuntimeError

        oldNumCores = parallel.getNP()

        parallel.setNP(numCores)
        parallel.setParallelType(pType)

        if numCores != oldNumCores:
            progressDialog = ProgressDialogSimple(self, self.tr('Case Redistribution'))

            progressDialog.setLabelText('Redistributing Case')

            redistributionTask = RedistributionTask()
            redistributionTask.progress.connect(progressDialog.setLabelText)

            progressDialog.open()

            await redistributionTask.redistribute()

            progressDialog.finish('Redistribution Done')

    def _load(self):
        numCores = parallel.getNP()
        self._ui.numberOfCores.setText(str(numCores))

        pType = parallel.getParallelType()

        if pType == ParallelType.LOCAL_MACHINE:
            self._ui.typeLocalMachine.setChecked(True)
            self._ui.stackedParameters.setCurrentIndex(_getStackIndex(ParallelType.LOCAL_MACHINE))
        elif pType == ParallelType.CLUSTER:
            self._ui.typeCluster.setChecked(True)
            self._ui.stackedParameters.setCurrentIndex(_getStackIndex(ParallelType.CLUSTER))
        elif pType == ParallelType.SLURM:
            self._ui.typeSlurm.setChecked(True)
            self._ui.stackedParameters.setCurrentIndex(_getStackIndex(ParallelType.SLURM))
        else:
            raise AssertionError

    @qasync.asyncSlot()
    async def _editHostFileClicked(self):
        _locationParent = Path(AppSettings.getRecentLocation()).resolve()

        self._dialogHostFile = EditHostfileDialog(self)
        self._dialogHostFile.open()

    @qasync.asyncSlot()
    async def _typeLocalMachineToggled(self, checked: bool):
        if checked:
            self._ui.stackedParameters.setCurrentIndex(ParallelType.LOCAL_MACHINE.value)

    @qasync.asyncSlot()
    async def _typeClusterToggled(self, checked: bool):
        if checked:
            self._ui.stackedParameters.setCurrentIndex(ParallelType.CLUSTER.value)
