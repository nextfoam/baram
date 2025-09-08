#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import qasync
import logging

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QLineEdit, QSizePolicy, QMessageBox
from PySide6.QtCore import Qt

from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem

from baramFlow.case_manager import CaseManager
from baramFlow.coredb.filedb import FileDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.project import Project
from baramFlow.view.widgets.content_page import ContentPage
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
        self.loadSnapshotCases(overwriteSlider=False)

    def _connectSignalsSlots(self):
        self._ui.buildROM.clicked.connect(self._selectCasesToBuildROM)
        self._ui.ROMReconstruct.clicked.connect(self._ROMReconstruct)

    def _disconnectSignalsSlots(self):
        pass

    def _selectCasesToBuildROM(self):
        self._listSelectorItemBatchCase = []
        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        if batchCasesDataFrame is None or len(batchCasesDataFrame) == 0:
            AsyncMessageBox().warning(self, self.tr('Reduced Order Model'),
                                            self.tr('Batch cases are required to build a reduced order model.'))
            return
        if GeneralDB.isTimeTransient():
            AsyncMessageBox().warning(self, self.tr('Reduced Order Model'),
                                            self.tr('ROM generation from transient simulation results is not yet supported.'))
            return

        batchStatuses = self._project.loadBatchStatuses()
        listCasename = batchCasesDataFrame.index.astype(str).tolist()
        listEndedCase = [name for name in listCasename if batchStatuses.get(name) == 'ENDED']
        if len(listEndedCase) == 0:
            AsyncMessageBox().warning(self, self.tr('Reduced Order Model'),
                                            self.tr('At least one completed case is required to build a reduced order model.'))
            return

        self._listSelectorItemBatchCase = [SelectorItem(name, name, i) for i, name in enumerate(listEndedCase)]

        self._dialog = MultiSelectorDialog(self, self.tr('Select Snapshot Cases'), self._listSelectorItemBatchCase, [])
        self._dialog.itemsSelected.connect(self._buildROM)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _buildROM(self, itemsFromDialog):
        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)

        nParam = len(batchCasesDataFrame.columns)
        if len(itemsFromDialog) < nParam + 1:
            confirm = await AsyncMessageBox().question(
                self, self.tr('Not enough snapshots'), self.tr('Snapshot cases seem insufficient for the given parameters, which may cause low ROM accuracy. Continue?'))
            if confirm != QMessageBox.StandardButton.Yes:
                return

        listSelectedName = [name for _, name in itemsFromDialog]
        snapshotCasesDataFrame = batchCasesDataFrame.loc[listSelectedName]

        progressDialog = ProgressDialog(self, self.tr('Reduced Order Model'), cancelable=True)
        self._caseManager.progress.connect(progressDialog.setLabelText)
        progressDialog.setLabelText(self.tr('Build ROM'))
        progressDialog.cancelClicked.connect(self._caseManager.cancel)
        progressDialog.open()

        self._project.fileDB().putDataFrame(FileDB.Key.SNAPSHOT_CASES.value, snapshotCasesDataFrame)

        try:
            await self._caseManager.podRunGenerateROM(listSelectedName)
            ROMdate = time.strftime("%Y-%m-%d, %H:%M:%S", time.localtime())
            ROMaccuracy = self._caseManager.podGetROMAccuracy()
            self._project.fileDB().putText("ROMdate", ROMdate)
            self._project.fileDB().putText("ROMaccuracy", ROMaccuracy)
            self.loadSnapshotCases(overwriteSlider=True)
            progressDialog.finish(self.tr('ROM build finished'))
        except Exception as e:
            progressDialog.finish(self.tr('ROM build error : ') + str(e))
        finally:
            self._caseManager.progress.disconnect(progressDialog.setLabelText)

    def loadSnapshotCases(self, overwriteSlider=True):
        self._snapshotCaseList.clear()
        self._snapshotCaseList.load()

        ROMdate = self._project.fileDB().getText("ROMdate")

        if ROMdate:
            ROMaccuracy = self._project.fileDB().getText("ROMaccuracy")
            strROMaccuracy = "{:.3e}".format(ROMaccuracy)
            if ROMaccuracy < 1.e6: strROMaccuracy += " (low accuracy)"
            textROMstatus = self.tr('ROM created on ') + ROMdate.decode("utf-8")
            textROMstatus += "\n" + self.tr('Accuracy: ') + strROMaccuracy
            self._ui.labelBuildROM.setText(textROMstatus)
            self._ui.snapshotCases.setVisible(True);
            self.generateSliders(overwriteSlider)
            self._ui.groupBox_Reconstruction.setEnabled(True);
        else:
            self._ui.labelBuildROM.setText(self.tr('ROM status: not created'))
            self._ui.snapshotCases.setVisible(False);
            self._ui.groupBox_Reconstruction.setEnabled(False);

        return

    def generateSliders(self, overwrite):
        if self._snapshotCaseList.parameters() is None: return

        layout = self._ui.verticalLayout_ReconstructGroup

        count = layout.count()
        if not overwrite and count > 1: return

        while count > 1:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            count -= 1

        self.listLineEdit = []

        listParam = self._snapshotCaseList.parameters().tolist()
        nParam = len(listParam)
        listCases = self._snapshotCaseList._cases

        for iParam in range(nParam):
            nameParam = listParam[iParam]
            valuesParam = [float(entry[nameParam]) for entry in listCases.values()]
            valueMinParam = min(valuesParam)
            valueMaxParam = max(valuesParam)
            new_widget = self.generateSingleSlider(iParam, nameParam, valueMinParam, valueMaxParam)
            layout.insertWidget(layout.count() - 1, new_widget)

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

        lineEdit = QLineEdit()
        lineEdit.setObjectName(f"lineEditPODParam{sliderIndex}")
        lineEdit.setFixedWidth(100)

        def sliderToLineEdit(value):
            ratio = value / 100.
            scaledValue = valueMinParam + ratio * (valueMaxParam - valueMinParam)
            lineEdit.blockSignals(True)
            lineEdit.setText(f"{scaledValue:.2f}")
            lineEdit.blockSignals(False)

        def lineEditToSlider():
            try:
                userVal = float(lineEdit.text())
                userVal = max(min(userVal, valueMaxParam), valueMinParam)
                lengthSlider = max(valueMaxParam - valueMinParam, 1.e-16)
                ratio = (userVal - valueMinParam) / (lengthSlider)
                sliderVal = int(round(ratio * 100.))
                slider.blockSignals(True)
                slider.setValue(sliderVal)
                slider.blockSignals(False)
            except ValueError:
                pass

        slider.valueChanged.connect(sliderToLineEdit)
        lineEdit.textChanged.connect(lineEditToSlider)

        h_layout.addWidget(label)
        h_layout.addWidget(slider)
        h_layout.addWidget(lineEdit)

        self.listLineEdit.append(lineEdit)

        sliderToLineEdit(slider.value())

        return container

    @qasync.asyncSlot()
    async def _ROMReconstruct(self):
        caseName = self._ui.nameCaseToReconstruct.text()
        if len(caseName) == 0:
            AsyncMessageBox().warning(self, self.tr('Reduced Order Model'),
                                            self.tr('Please specify a case name to reconstruct.'))
            return

        if GeneralDB.isTimeTransient():
            confirm = await AsyncMessageBox().question(
                self, self.tr('Outdated ROM'), self.tr('The current ROM model is an outdated version based on steady simulation results. Continue?'))
            if confirm != QMessageBox.StandardButton.Yes:
                return

        progressDialog = ProgressDialog(self, self.tr('Reduced Order Model'), cancelable=True)
        self._caseManager.progress.connect(progressDialog.setLabelText)
        progressDialog.setLabelText(self.tr('Reconstruct from ROM'))
        progressDialog.cancelClicked.connect(self._caseManager.cancel)
        progressDialog.open()

        listSnapshotCase = self._snapshotCaseList._cases
        paramsToReconstruct = {}
        listParam = self._snapshotCaseList.parameters().tolist()
        for iParam, nameParam in enumerate(listParam):
            valueParam = float(self.listLineEdit[iParam].text())
            paramsToReconstruct[nameParam] = valueParam

        try:
            await self._caseManager.podInitReconstructedCase(caseName, paramsToReconstruct)
            await self._caseManager.podRunReconstruct(caseName, listSnapshotCase, paramsToReconstruct)
            await self._caseManager.podSaveToBatchCase(caseName)
            await self._caseManager.podAddToBatchList(caseName, paramsToReconstruct)
            progressDialog.finish(self.tr('Reconstruction Finished'))
        except Exception as e:
            progressDialog.finish(self.tr('ROM reconstruction error : ') + str(e))
        finally:
            self._caseManager.progress.disconnect(progressDialog.setLabelText)

    def closeEvent(self, event):
        self._disconnectSignalsSlots()
        self._snapshotCaseList.close()

        super().closeEvent(event)