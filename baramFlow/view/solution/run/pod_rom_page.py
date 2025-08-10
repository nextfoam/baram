#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import platform
import time
import qasync
import logging
from enum import Enum, auto

import pandas as pd
from PySide6.QtWidgets import QFileDialog, QWidget, QHBoxLayout, QLabel, QSlider, QLineEdit, QSizePolicy
from PySide6.QtCore import Qt

from widgets.async_message_box import AsyncMessageBox
from widgets.list_table import ListItem
from widgets.progress_dialog import ProgressDialog
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem

from baramFlow.case_manager import CaseManager, BatchCase
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.filedb import FileDB
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.openfoam.case_generator import CanceledException
from baramFlow.openfoam.constant.turbulence_properties import TurbulenceProperties
from baramFlow.openfoam.solver import SolverNotFound
from baramFlow.openfoam.system.control_dict import ControlDict
from baramFlow.openfoam.system.fv_options import FvOptions
from baramFlow.openfoam.system.fv_schemes import FvSchemes
from baramFlow.openfoam.system.fv_solution import FvSolution
from baramFlow.view.widgets.content_page import ContentPage
from .batch_case_list import BatchCaseList
from .snapshot_case_list import SnapshotCaseList
from .pod_rom_page_ui import Ui_PODROMPage


logger = logging.getLogger(__name__)

SOLVER_CHECK_INTERVAL = 3000


class PODROMPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_PODROMPage()
        self._ui.setupUi(self)

        self._listSelectorItemBatchCase = []
        self._snapshotCaseList = SnapshotCaseList(self, self._ui.snapshotCaseList)

        self._project = Project.instance()

        self._stopDialog = None
        self._dialog = None

        self._runningMode = None
        self._userParameters = None

        self._caseManager = CaseManager()

        self._connectSignalsSlots()

        self._snapshotCaseList.load()

        self.listLineEdit = []

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _load(self):
        self.loadSnapshotCases()
        self.generateSliders()

    def _connectSignalsSlots(self):
        self._ui.buildROM.clicked.connect(self._selectCasesToBuildROM)
        self._ui.ROMReconstruct.clicked.connect(self._ROMReconstruct)
        return

    def _disconnectSignalsSlots(self):
        # self._project.solverStatusChanged.disconnect(self._statusChanged)
        # self._caseManager.caseLoaded.disconnect(self._caseLoaded)
        return

    def _selectCasesToBuildROM(self):
        self._listSelectorItemBatchCase = []
        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        batchCasesDict = batchCasesDataFrame.to_dict(orient='index')
        for idx, (key, value) in enumerate(batchCasesDict.items()):
            self._listSelectorItemBatchCase.append(SelectorItem(key, key, idx))

        self._dialog = MultiSelectorDialog(self, self.tr('Select Snapshot Cases'), self._listSelectorItemBatchCase, [])
        self._dialog.itemsSelected.connect(self._runBuildROM)
        self._dialog.open()

    def _runBuildROM(self, items):
        self._buildROM(items)

    @qasync.asyncSlot()
    async def _buildROM(self, itemsFromDialog):
        progressDialog = ProgressDialog(self, self.tr('Build ROM'), True)
        self._caseManager.progress.connect(progressDialog.setLabelText)
        progressDialog.cancelClicked.connect(self._caseManager.cancel)
        progressDialog.open()

        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        batchCasesDict = batchCasesDataFrame.to_dict(orient='index')
        listSelectedName = [name for _, name in itemsFromDialog]
        listSelectedCase = [(name, batchCasesDict[name]) for name in batchCasesDict if name in listSelectedName]

        self._project.fileDB().putDataFrame(FileDB.Key.SNAPSHOT_CASES.value, pd.DataFrame.from_dict(dict(listSelectedCase), orient='index'))
        self.loadSnapshotCases()

        try:
            await self._caseManager.podRunGenerateROM(listSelectedCase)
            progressDialog.finish(self.tr('Calculation started'))
        except Exception as e:
            progressDialog.finish(self.tr('POD run error : ') + str(e))
        finally:
            self._caseManager.progress.disconnect(progressDialog.setLabelText)

    def loadSnapshotCases(self):
        self._snapshotCaseList.clear()
        self._snapshotCaseList.load()
        self._ui.labelBuildROM.setText(self.tr('ROM Accuracy : ') + self._caseManager.podGetROMAccuracy())
        return

    def generateSliders(self):
        if len(self.listLineEdit) > 0: return
        
        listParam = self._snapshotCaseList._parameters.tolist()
        nParam = len(listParam)
        listCases = self._snapshotCaseList._cases
        
        for iParam in range(nParam):
            nameParam = listParam[iParam]
            valuesParam = [float(entry[nameParam]) for entry in listCases.values()]
            valueMinParam = min(valuesParam)
            valueMaxParam = max(valuesParam)
            new_widget = self.generateSingleSlider(iParam, nameParam, valueMinParam, valueMaxParam)
            self._ui.verticalLayout_PODROMpage.insertWidget(2+iParam, new_widget)
        
        return

    def generateSingleSlider(self, sliderIndex, nameParam, valueMinParam, valueMaxParam):
        container = QWidget()
        h_layout = QHBoxLayout()
        container.setLayout(h_layout)
    
        label = QLabel(nameParam)
        label.setObjectName(f"labelPODParam{sliderIndex}")
        label.setFixedWidth(50)
    
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName(f"sliderPODParam{sliderIndex}")
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setSingleStep(1)
        slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
        slider.valueMinParam = valueMinParam
        slider.valueMaxParam = valueMaxParam
    
        lineedit = QLineEdit()
        lineedit.setObjectName(f"lineeditPODParam{sliderIndex}")
        lineedit.setFixedWidth(100)
    
        def sliderToLineEdit(value):
            ratio = value / 100.
            scaled_value = valueMinParam + ratio * (valueMaxParam - valueMinParam)
            lineedit.blockSignals(True)
            lineedit.setText(f"{scaled_value:.2f}")
            lineedit.blockSignals(False)
    
        def lineEditToSlider():
            try:
                user_val = float(lineedit.text())
                user_val = max(min(user_val, valueMaxParam), valueMinParam)
                ratio = (user_val - valueMinParam) / (valueMaxParam - valueMinParam)
                slider_val = int(round(ratio * 100.))
                slider.blockSignals(True)
                slider.setValue(slider_val)
                slider.blockSignals(False)
            except ValueError:
                pass
    
        slider.valueChanged.connect(sliderToLineEdit)
        lineedit.textChanged.connect(lineEditToSlider)
    
        h_layout.addWidget(label)
        h_layout.addWidget(slider)
        h_layout.addWidget(lineedit)
        
        self.listLineEdit.append(lineedit)
    
        sliderToLineEdit(slider.value())
    
        return container

    @qasync.asyncSlot()
    async def _ROMReconstruct(self):
        import traceback
        progressDialog = ProgressDialog(self, self.tr('Reconstruct with ROM'), True)
        self._caseManager.progress.connect(progressDialog.setLabelText)
        progressDialog.cancelClicked.connect(self._caseManager.cancel)
        progressDialog.open()
        
        listSnapshotCase = self._snapshotCaseList._cases
        paramsToReconstruct = {}
        listParam = self._snapshotCaseList._parameters.tolist()
        nParam = len(listParam)
        for iParam in range(nParam):
            valueParam = float(self.listLineEdit[iParam].text())
            nameParam = listParam[iParam]
            paramsToReconstruct[nameParam] = valueParam

        try:
            await self._caseManager.podRunReconstruct(listSnapshotCase, paramsToReconstruct)
            # self._batchCaseList._setCase("pod-reconstructed", caseToReconstruct, SolverStatus.ENDED)
            # self._batchCaseList._listChanged(True)
            # self._project.updateBatchStatuses(
                # {name: item.status().name for name, item in self._batchCaseList._items.items() if item.status()})
            progressDialog.finish(self.tr('Calculation started'))
        except Exception as e:
            progressDialog.finish(self.tr('POD run error : ') + str(e))
            traceback.print_exc()  # 전체 traceback 출력
        finally:
            self._caseManager.progress.disconnect(progressDialog.setLabelText)
        return