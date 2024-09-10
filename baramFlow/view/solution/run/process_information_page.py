#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import platform
import time
import qasync
import logging
from enum import Enum, auto

import pandas as pd
from PySide6.QtWidgets import QFileDialog

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.openfoam.constant.turbulence_properties import TurbulenceProperties
from baramFlow.openfoam.system.fv_options import FvOptions
from widgets.async_message_box import AsyncMessageBox
from widgets.list_table import ListItem
from widgets.progress_dialog import ProgressDialog

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.openfoam.solver import SolverNotFound
from baramFlow.openfoam.case_generator import CanceledException
from baramFlow.openfoam.system.fv_solution import FvSolution
from baramFlow.openfoam.system.control_dict import ControlDict
from baramFlow.openfoam.system.fv_schemes import FvSchemes
from baramFlow.view.widgets.content_page import ContentPage
from .batch_case_list import BatchCaseList
from .batch_cases_import_dialog import BatchCasesImportDialog
from .process_information_page_ui import Ui_ProcessInformationPage
from .user_parameters_dialog import UserParametersDialog


logger = logging.getLogger(__name__)

SOLVER_CHECK_INTERVAL = 3000


class RunningMode(Enum):
    LIVE_RUNNING_MODE = auto()
    BATCH_RUNNING_MODE = auto()


class ProcessInformationPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)

        self._batchCaseList = BatchCaseList(self, self._ui.batchCaseList)

        self._project = Project.instance()

        self._stopDialog = None
        self._dialog = None

        self._runningMode = None
        self._userParameters = None

        self._caseManager = CaseManager()

        self._ui.calculation.setMinimumWidth(self.parent().width() - 30)
        self._connectSignalsSlots()

        self._batchCaseList.load()
        self._setRunningMode(RunningMode.LIVE_RUNNING_MODE)

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _load(self):
        self._statusChanged(self._caseManager.status(), None, False)
        self._updateUserParameters()

    def _connectSignalsSlots(self):
        self._ui.startCalculation.clicked.connect(self._startCalculationClicked)
        self._ui.cancelCalculation.clicked.connect(self._cancelCalculationClicked)
        self._ui.saveAndStopCalculation.clicked.connect(self._saveAndStopCalculationClicked)
        self._ui.updateConfiguration.clicked.connect(self._updateConfigurationClicked)
        self._ui.userParametersGroup.toggled.connect(self._toggleUserParameters)
        self._ui.editUserParametrer.clicked.connect(self._editUserParameters)
        self._ui.toLiveMode.clicked.connect(self._toLiveMode)
        self._ui.toBatchMode.clicked.connect(self._toBatchMode)
        self._ui.exportBatchCase.clicked.connect(self._openExportDialog)
        self._ui.importBatchCases.clicked.connect(self._openImportDialog)
        self._project.solverStatusChanged.connect(self._statusChanged)
        self._caseManager.caseLoaded.connect(self._caseLoaded)

    def _setRunningMode(self, mode):
        if mode == RunningMode.LIVE_RUNNING_MODE:
            self._ui.updateConfiguration.show()
            self._ui.batchCases.hide()
            self._ui.toBatchMode.show()
            self._ui.toLiveMode.hide()
        else:
            self._ui.updateConfiguration.hide()
            self._ui.batchCases.show()
            self._ui.toBatchMode.hide()
            self._ui.toLiveMode.show()

        self._runningMode = mode

    @qasync.asyncSlot()
    async def _startCalculationClicked(self):
        if self._runningMode == RunningMode.LIVE_RUNNING_MODE:
            progressDialog = ProgressDialog(self, self.tr('Calculation Run.'), True)

            self._caseManager.progress.connect(progressDialog.setLabelText)
            progressDialog.cancelClicked.connect(self._caseManager.cancel)
            progressDialog.open()

            try:
                await self._caseManager.liveRun()
                progressDialog.finish(self.tr('Calculation started'))
            except SolverNotFound as e:
                progressDialog.finish(self.tr('Case generating fail. - ') + str(e))
            except CanceledException:
                progressDialog.finish(self.tr('Calculation cancelled'))
            except RuntimeError as r:
                progressDialog.finish(str(r))
        else:
            cases = self._batchCaseList.batchSchedule()
            if not cases:
                await AsyncMessageBox().information(self, self.tr('Batch Calculation'),
                                                    self.tr('No case is scheduled.'))
                return

            self._updateStatus(SolverStatus.RUNNING)
            await self._caseManager.batchRun(cases)
            self._updateStatus(SolverStatus.NONE)

    def _cancelCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'noWriteNow'
        controlDict.writeAtomic()

        if self._runningMode == RunningMode.BATCH_RUNNING_MODE:
            self._caseManager.stopBatchRun()

        self._waitingStop()

    def _saveAndStopCalculationClicked(self):
        controlDict = ControlDict().build()
        controlDict.asDict()['stopAt'] = 'writeNow'
        controlDict.writeAtomic()

        if self._runningMode == RunningMode.BATCH_RUNNING_MODE:
            self._caseManager.stopBatchRun()

        self._waitingStop()

    def _waitingStop(self):
        self._stopDialog = ProgressDialog(self, self.tr('Calculation Canceling'))
        self._stopDialog.open()

        self._stopDialog.setLabelText(
            self.tr('Waiting for the solver to stop after final calculation. You can "Force Stop",\n'
                    'yet it could corrupt the final iteration result.'))
        self._stopDialog.showCancelButton(self.tr('Force Stop'))
        self._stopDialog.cancelClicked.connect(self._forceStop)

    def _forceStop(self):
        self._caseManager.kill()

    def _updateConfigurationClicked(self):
        regions = coredb.CoreDB().getRegions()
        for rname in regions:
            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()
            FvOptions(rname).build().write()

            region = CoreDBReader().getRegionProperties(rname)
            if region.isFluid():
                TurbulenceProperties(rname).build().write()

        ControlDict().build().writeAtomic()

    def _toggleUserParameters(self, checked):
        self._ui.userParameters.setVisible(checked)

    def _editUserParameters(self):
        self._dialog = UserParametersDialog(self, self._userParameters)
        self._dialog.accepted.connect(self._updateUserParameters)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _toLiveMode(self):
        self._setRunningMode(RunningMode.LIVE_RUNNING_MODE)

        # progressDialog = ProgressDialog(self, self.tr('Case Loading'))
        # app.case.progress.connect(progressDialog.setLabelText)
        # progressDialog.open()
        #
        self._caseManager.loadLiveCase()
        #
        # progressDialog.close()

    @qasync.asyncSlot()
    async def _toBatchMode(self):
        if platform.system() == 'Windows' and not ctypes.windll.shell32.IsUserAnAdmin():
            # Symbolic link requires administrator permission on Windows platform
            await AsyncMessageBox().warning(
                self, self.tr('Permission Error'), self.tr('Run BARAM as administrator to enter batch mode'))
            return

        self._setRunningMode(RunningMode.BATCH_RUNNING_MODE)

    @qasync.asyncSlot()
    async def _openExportDialog(self):
        if not self._userParameters:
            await AsyncMessageBox().information(
                self, self.tr('Export Batch Cases'), self.tr('No batch parameter is defined.'))
            return

        self._dialog = QFileDialog(self, self.tr('Export Batch Parameters'), '', self.tr('Excel (*.xlsx);; CSV (*.csv)'))
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.fileSelected.connect(self._exportBatchCase)
        self._dialog.open()

    def _openImportDialog(self):
        self._dialog = BatchCasesImportDialog(self, self._batchCaseList.parameters())
        self._dialog.accepted.connect(self._importBatchCase)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _statusChanged(self, status, name=None, liveStatusChanged=False):
        if self._runningMode == RunningMode.BATCH_RUNNING_MODE:
            self._batchCaseList.updateStatus(status, name)
        else:
            self._updateStatus(status)

    def _updateStatus(self, status):
        if status == SolverStatus.WAITING:
            text = self.tr('Waiting')
        elif status == SolverStatus.RUNNING:
            text = self.tr('Running')
        else:
            text = self.tr('Not Running')
            if self._stopDialog is not None:
                self._stopDialog.close()
                self._stopDialog = None

        process = self._caseManager.process()
        if process:
            pid = str(process.pid)
            createTime = time.strftime("%Y-%m-%d, %H:%M:%S", time.localtime(process.startTime))
        else:
            pid = '-'
            createTime = '-'

        self._ui.id.setText(pid)
        self._ui.createTime.setText(createTime)
        self._ui.status.setText(text)

        if status == SolverStatus.WAITING or status == SolverStatus.RUNNING:
            self._ui.startCalculation.hide()
            self._ui.cancelCalculation.show()
            self._ui.saveAndStopCalculation.setEnabled(True)
            self._ui.updateConfiguration.setEnabled(True)
            self._ui.userParametersGroup.setDisabled(True)
            self._ui.batchCases.setDisabled(True)
            self._ui.runningMode.setDisabled(True)
        else:
            self._ui.startCalculation.show()
            self._ui.cancelCalculation.hide()
            self._ui.saveAndStopCalculation.setDisabled(True)
            self._ui.updateConfiguration.setDisabled(True)
            self._ui.userParametersGroup.setEnabled(True)
            self._ui.batchCases.setEnabled(True)
            self._ui.runningMode.setEnabled(True)

    @qasync.asyncSlot()
    async def _caseLoaded(self, name):
        self._batchCaseList.setCurrentCase(name)

    def _updateUserParameters(self):
        self._userParameters = coredb.CoreDB().getBatchParameters()

        self._ui.userParameterList.clear()
        for name, data in self._userParameters.items():
            self._ui.userParameterList.addItem(ListItem(name, [f'{name} ({data["usages"]})', data['value']]))

    def _exportBatchCase(self, file):
        df = self._batchCaseList.exportAsDataFrame()
        if df.empty:
            columns = ['Case Name'] + list(self._userParameters.keys())
            df = pd.DataFrame(columns=columns)
            df.set_index(columns[0], inplace=True)

        if file.endswith('xlsx'):
            df.to_excel(file, index_label='Case Name')
        else:
            df.to_csv(file, sep=',', index_label='Case Name')

    @qasync.asyncSlot()
    async def _importBatchCase(self):
        if self._dialog.isClearChecked():
            self._batchCaseList.clear()

        self._caseManager.loadLiveCase()
        self._batchCaseList.importFromDataFrame(self._dialog.cases())
