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

from baramFlow.case_manager import CaseManager, BatchCase
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_reader import CoreDBReader
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
from .user_parameters_dialog import UserParametersDialog


logger = logging.getLogger(__name__)

SOLVER_CHECK_INTERVAL = 3000


class PODROMPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_PODROMPage()
        self._ui.setupUi(self)

        ### batchCaseList를 참조할 수 없는 상태
        # self._batchCaseList = BatchCaseList(self, self._ui.batchCaseList)
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
        self._ui.ROMReconstruct.clicked.connect(self._ROMReconstruct)
        return

    def _disconnectSignalsSlots(self):
        # self._project.solverStatusChanged.disconnect(self._statusChanged)
        # self._caseManager.caseLoaded.disconnect(self._caseLoaded)
        return

    def loadSnapshotCases(self):
        self._snapshotCaseList.load()
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
            self._ui.verticalLayout_PODROMpage.insertWidget(1+iParam, new_widget)
        
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
        progressDialog = ProgressDialog(self, self.tr('Reconstruct with ROM'), True)
        self._caseManager.progress.connect(progressDialog.setLabelText)
        progressDialog.cancelClicked.connect(self._caseManager.cancel)
        progressDialog.open()
        
        listSnapshotCase = self._snapshotCaseList._cases
        caseToReconstruct = ()
        listParam = self._snapshotCaseList._parameters.tolist()
        nParam = len(listParam)
        for iParam in range(nParam):
            valueParam = float(self.listLineEdit[iParam].text())
            caseToReconstruct += (valueParam, )
        
        try:
            await self._caseManager.loadBatchCase(caseToReconstruct)
            await self._caseManager.podRunReconstruct(listSnapshotCase, caseToReconstruct)
            ### batchCaseList를 참조할 수 없는 상태
            self._batchCaseList._setCase("pod-reconstructed", caseToReconstruct, SolverStatus.ENDED)
            self._batchCaseList._listChanged(True)
            self._project.updateBatchStatuses(
                {name: item.status().name for name, item in self._batchCaseList._items.items() if item.status()})
            progressDialog.finish(self.tr('Calculation started'))
        except Exception as e:
            progressDialog.finish(self.tr('POD run error : ') + str(e))
        finally:
            self._caseManager.progress.disconnect(progressDialog.setLabelText)
        return