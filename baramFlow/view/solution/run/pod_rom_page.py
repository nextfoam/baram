#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import qasync
import logging
import numpy as np

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
        self._paramActive = {}
        self._selectedSnapshotCases = []

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
        self._dialog.itemsSelected.connect(self._onSnapshotCasesSelected)
        self._dialog.open()

    def _onSnapshotCasesSelected(self, itemsFromDialog):
        self._selectedSnapshotCases = [name for _, name in itemsFromDialog]
        batchCasesDF = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        if batchCasesDF is None or batchCasesDF.empty:
            return
        paramNames = batchCasesDF.columns.tolist()

        self._paramActive = {p: True for p in paramNames}
        items = [SelectorItem(p, p, i) for i, p in enumerate(paramNames)]

        self._dialog = MultiSelectorDialog(self, self.tr('Select Parameters to Use'), items, [])
        self._dialog.itemsSelected.connect(self._onParamsSelected)
        self._dialog.open()

    def _onParamsSelected(self, itemsFromDialog):
        active = [name for _, name in itemsFromDialog]
        batchCasesDF = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        allParams = batchCasesDF.columns.tolist() if batchCasesDF is not None else active
        self._paramActive = {p: (p in active) for p in allParams}
        self._buildROM(self._selectedSnapshotCases)

    @qasync.asyncSlot()
    async def _buildROM(self, itemsFromDialog):
        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)

        if itemsFromDialog and isinstance(itemsFromDialog[0], tuple):
            listSelectedName = [name for _, name in itemsFromDialog]
        else:
            listSelectedName = list(itemsFromDialog)

        nParam = len(batchCasesDataFrame.columns)
        if len(listSelectedName) < nParam + 1:
            confirm = await AsyncMessageBox().question(
                self, self.tr('Not enough snapshots'), self.tr('Snapshot cases seem insufficient for the given parameters, which may cause low ROM accuracy. Continue?'))
            if confirm != QMessageBox.StandardButton.Yes:
                return

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
            activeNames = [p for p, v in self._paramActive.items() if v]
            self._project.fileDB().putText("ROMparams", "\n".join(activeNames))
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
            activeNames = self._project.fileDB().getText("ROMparams").decode("utf-8").split("\n")
            self._paramActive = {name: True for name in activeNames}
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
        if not self._paramActive:
            self._paramActive = {p: True for p in listParam}
        nParam = len(listParam)
        listCases = self._snapshotCaseList._cases

        for iParam in range(nParam):
            nameParam = listParam[iParam]
            valuesParam = [float(entry[nameParam]) for entry in listCases.values()]
            valueMinParam = min(valuesParam)
            valueMaxParam = max(valuesParam)
            isActive = bool(self._paramActive.get(nameParam, False))
            new_widget = self.generateSingleSlider(iParam, nameParam, valueMinParam, valueMaxParam, visible=isActive)
            layout.insertWidget(layout.count() - 1, new_widget)

        return

    def generateSingleSlider(self, sliderIndex, nameParam, valueMinParam, valueMaxParam, visible=True):
        container = QWidget()
        h_layout = QHBoxLayout()
        container.setLayout(h_layout)
        container.setVisible(visible)

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
            if self._paramActive.get(nameParam, False):
                valueParam = float(self.listLineEdit[iParam].text())
                paramsToReconstruct[nameParam] = valueParam

        inferred = self._inferInactiveParamsLinear(
            listSnapshotCase=listSnapshotCase,
            allParams=listParam,
            activeMask=self._paramActive,
            userActiveValues=paramsToReconstruct
        )
        paramsToReconstruct.update(inferred)

        activeNames = [p for p,v in self._paramActive.items() if v]
        paramsActive = {p: paramsToReconstruct[p] for p in activeNames}

        try:
            await self._caseManager.podInitReconstructedCase(caseName, paramsToReconstruct)
            await self._caseManager.podRunReconstruct(caseName, listSnapshotCase, paramsActive)
            await self._caseManager.podSaveToBatchCase(caseName)
            await self._caseManager.podAddToBatchList(caseName, paramsToReconstruct)
            progressDialog.finish(self.tr('Reconstruction Finished'))
        except Exception as e:
            progressDialog.finish(self.tr('ROM reconstruction error : ') + str(e))
        finally:
            self._caseManager.progress.disconnect(progressDialog.setLabelText)

    def _inferInactiveParamsLinear(self, listSnapshotCase, allParams, activeMask, userActiveValues, k=None):
        """
        listSnapshotCase: dict[caseName] -> {paramName: value}
        allParams: [paramName,...]
        activeMask: {paramName: bool}
        userActiveValues: {activeParamName: float}
        returns: {inactiveParamName: float}
        """
        activeNames = [p for p in allParams if activeMask.get(p, False)]
        inactiveNames = [p for p in allParams if not activeMask.get(p, False)]
        if not inactiveNames:
            return {}

        rows = list(listSnapshotCase.values())
        n = len(rows)
        d = len(activeNames)

        # Build feature matrix (active params)
        if d > 0:
            X = np.array([[float(r[p]) for p in activeNames] for r in rows], dtype=float)
            mu = X.mean(axis=0)
            std = X.std(axis=0)
            std[std == 0.0] = 1.0
            Xs = (X - mu) / std
            x_t = np.array([float(userActiveValues[p]) for p in activeNames], dtype=float)
            xs = (x_t - mu) / std
            # distances & neighbor selection
            dist = np.linalg.norm(Xs - xs, axis=1)
            if k is None:
                k = min(max(2*max(d,1), 8), n)
            nn_idx = np.argsort(dist)[:k]
            Xk = Xs[nn_idx, :]             # (k x d)
        else:
            # no active features -> intercept-only model; use first k or all
            if k is None:
                k = min(8, n)
            nn_idx = np.arange(min(k, n))
            Xk = np.zeros((len(nn_idx), 0))

        inferred = {}
        for p in inactiveNames:
            y_all = np.array([float(r[p]) for r in rows], dtype=float)
            yk = y_all[nn_idx]             # (k,)

            if Xk.shape[1] == 0:
                # mean of neighbors (intercept only)
                y_pred = float(np.mean(yk)) if yk.size else float(np.mean(y_all))
            else:
                # Try OLS with intercept
                A = np.hstack([Xk, np.ones((Xk.shape[0], 1))])  # (k x (d+1))
                rank = np.linalg.matrix_rank(A)
                if rank >= min(A.shape):
                    beta, _, _, _ = np.linalg.lstsq(A, yk, rcond=None)
                    y_pred = float(np.dot(np.append(xs, 1.0), beta))
                else:
                    # PCA reduction on neighbors, then linear regression with intercept
                    Xc = Xk - Xk.mean(axis=0, keepdims=True)
                    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
                    tol = 1e-8
                    r = int(np.sum(S > tol))
                    r = max(1, min(r, Xk.shape[0]-1, Xk.shape[1]))
                    Z = U[:, :r] * S[:r]              # (k x r)
                    B = np.hstack([Z, np.ones((Z.shape[0], 1))])  # add intercept
                    beta, _, _, _ = np.linalg.lstsq(B, yk, rcond=None)
                    x_center = xs - Xk.mean(axis=0)
                    z_t = x_center @ Vt[:r].T         # (r,)
                    y_pred = float(np.dot(np.append(z_t, 1.0), beta))

            # clamp to observed range for stability
            vmin, vmax = float(y_all.min()), float(y_all.max())
            if y_pred < vmin: y_pred = vmin
            if y_pred > vmax: y_pred = vmax
            inferred[p] = str(y_pred)

        return inferred

    def closeEvent(self, event):
        self._disconnectSignalsSlots()
        self._snapshotCaseList.close()

        super().closeEvent(event)