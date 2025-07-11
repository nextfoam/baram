#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QMessageBox

from libbaram.mpi import ParallelType
from widgets.radio_group import RadioGroup

from .edit_hostfile_dialog import EditHostfileDialog
from .parallel_environment_dialog_ui import Ui_parallelEnvironmentDialog


_stackIndex = {
    ParallelType.LOCAL_MACHINE: 0,
    ParallelType.CLUSTER: 1,
    ParallelType.SLURM: 2
}


class ParallelEnvironmentDialog(QDialog):
    def __init__(self, parent, environment):
        """Constructs parallel environment dialog.
        """
        super().__init__(parent)

        self._parent = parent
        self._environment = environment

        self._ui = Ui_parallelEnvironmentDialog()
        self._ui.setupUi(self)

        self._typeRadios = RadioGroup(self._ui.typeRadios)

        self._connectSignalsSlots()

        self._load()

    def environment(self):
        return self._environment

    def setReadOnly(self, readOnly=True):
        if readOnly:
            self._ui.dialogContents.setEnabled(False)
            self._ui.applyButton.setEnabled(False)
        else:
            self._ui.dialogContents.setEnabled(True)
            self._ui.applyButton.setEnabled(True)

    def _connectSignalsSlots(self):
        self._ui.editHostFile.clicked.connect(self._editHostFileClicked)

        self._typeRadios.valueChanged.connect(self._typeChanged)

        self._ui.applyButton.clicked.connect(self.apply)
        self._ui.closeButton.clicked.connect(self.close)

    @qasync.asyncSlot()
    async def apply(self):
        try:
            numCores = int(self._ui.numberOfCores.text())
        except ValueError:
            QMessageBox.critical(self, self.tr('Input Error'), self.tr('Error in Number of Cores'))
            return

        if numCores <= 0:
            QMessageBox.critical(self, self.tr('Input Error'), self.tr('Number of Cores should be greater than 0'))
            return

        self._environment.setNP(numCores)
        self._environment.setType(ParallelType[self._typeRadios.value()])

        self.accepted.emit()

    def _load(self):
        numCores = self._environment.np()
        self._ui.numberOfCores.setText(str(numCores))

        self._typeRadios.setObjectMap({
            'typeLocalMachine': ParallelType.LOCAL_MACHINE.name,
            'typeCluster': ParallelType.CLUSTER.name,
            'typeSlurm': ParallelType.SLURM.name
        }, self._environment.type().name)

    @qasync.asyncSlot()
    async def _editHostFileClicked(self):
        self._dialogHostFile = EditHostfileDialog(self, self._environment)
        self._dialogHostFile.open()

    @qasync.asyncSlot()
    async def _typeChanged(self, pType):
        self._ui.stackedParameters.setCurrentIndex(_stackIndex[ParallelType[pType]])
