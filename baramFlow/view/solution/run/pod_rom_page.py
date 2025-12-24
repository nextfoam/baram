#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import qasync
import logging
import numpy as np
import re
import os
import uuid
from pathlib import Path
import pandas as pd

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QLineEdit, QSizePolicy, QMessageBox, QTableWidgetItem, QHeaderView, QFileDialog
from PySide6.QtCore import Qt

from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem

from baramFlow.case_manager import CaseManager, BatchCase
from baramFlow.coredb.filedb import FileDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.project import Project
from baramFlow.view.widgets.content_page import ContentPage
from .snapshot_case_list import SnapshotCaseList
from .pod_rom_page_ui import Ui_PODROMPage
from .eval_enhance_rom_dialog import EvalNEnhanceROMDialog

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.monitor_db import DirectionSpecificationMethod
from baramFlow.coredb.reference_values_db import ReferenceValuesDB

from baramFlow.base.constants import VectorComponent, FieldType
from baramFlow.base.field import VELOCITY, CollateralField, Field, SpecieField, UserScalarField
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.function_objects.components import foComponentsReport
from baramFlow.openfoam.function_objects.force_coeffs import foForceCoeffsReport
from baramFlow.openfoam.post_processing.post_file_reader import readPostFile
from baramFlow.openfoam.solver import findSolver

from baramFlow.openfoam.function_objects.probes import foProbesReport
from baramFlow.openfoam.function_objects.patch_probes import foPatchProbesReport
from baramFlow.openfoam.function_objects.surface_field_value import (
    SurfaceReportType,
    foSurfaceFieldValueReport,
)
from baramFlow.openfoam.function_objects.vol_field_value import (
    VolumeReportType,
    VolumeType,
    foVolFieldValueReport,
)
from baramFlow.openfoam.solver_field import getSolverFieldName, getSolverComponentName
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB

from baramFlow.libbaram.collateral_fields import collateralFieldDict
from baramFlow.openfoam.function_objects.read_fields import foReadFieldsReport
from baramFlow.openfoam.function_objects.mag import foMagReport

from libbaram import utils
from libbaram.natural_name_uuid import uuidToNnstr
from libbaram.math import calucateDirectionsByRotation
from libbaram.run import runParallelUtility


logger = logging.getLogger(__name__)

SOLVER_CHECK_INTERVAL = 3000
ROM_EVAL_RESULTS_KEY = "ROM_EVAL_RESULTS"


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

        self._initEvalResultTable()
        self._loadEvalResultTable()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _load(self):
        self.loadSnapshotCases(overwriteSlider=False)

    def _connectSignalsSlots(self):
        self._ui.buildROM.clicked.connect(self._selectCasesToBuildROM)
        self._ui.ROMReconstruct.clicked.connect(self._ROMReconstruct)
        self._ui.EvalNEnhanceROM.clicked.connect(self._setEvalNEnhanceROM)
        self._ui.exportEvalROM.clicked.connect(self._openExportDialog)

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
        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        if batchCasesDataFrame is None or batchCasesDataFrame.empty:
            return
        paramNames = batchCasesDataFrame.columns.tolist()

        self._paramActive = {p: True for p in paramNames}
        items = [SelectorItem(p, p, i) for i, p in enumerate(paramNames)]

        self._dialog = MultiSelectorDialog(self, self.tr('Select Parameters to Use'), items, [])
        self._dialog.itemsSelected.connect(self._onParamsSelected)
        self._dialog.open()

    def _onParamsSelected(self, itemsFromDialog):
        active = [name for _, name in itemsFromDialog]
        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        allParams = batchCasesDataFrame.columns.tolist() if batchCasesDataFrame is not None else active
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

    def _setEvalNEnhanceROM(self):
        self._dialog = EvalNEnhanceROMDialog(self)
        self._dialog.settingsCompleted.connect(self._EvalNEnhanceROM)
        self._dialog.open()

    def _initEvalResultTable(self):
        table = self._ui.tblRomEval
        table.setRowCount(6)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([
            self.tr("ROM"),
            self.tr("CFD"),
            self.tr("Err. (%)"),
        ])
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

    def _loadEvalResultTable(self):
        table = self._ui.tblRomEval
        button = self._ui.exportEvalROM

        df = self._project.fileDB().getDataFrame(ROM_EVAL_RESULTS_KEY)
        if df is None or df.empty:
            table.setRowCount(0)
            table.setVisible(False)
            button.setVisible(False)
            return

        self._updateEvalResultTableFromDataFrame(df)

    def _updateEvalResultTableFromDataFrame(self, df):
        table = self._ui.tblRomEval
        button = self._ui.exportEvalROM

        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([
            self.tr("ROM"),
            self.tr("CFD"),
            self.tr("Err. (%)"),
        ])

        df_local = df.reset_index(drop=True)

        nrow = len(df_local)
        table.setRowCount(nrow)

        for i in range(nrow):
            row = df_local.iloc[i]

            label = str(row.get("metricLabel", "")) or ""
            rom_val = row.get("rom", "")
            cfd_val = row.get("cfd", "")
            rel_val = row.get("relErrPercent", "")

            table.setVerticalHeaderItem(i, QTableWidgetItem(label))

            table.setItem(i, 0, QTableWidgetItem(f"{rom_val:.{4}g}"))
            table.setItem(i, 1, QTableWidgetItem(f"{cfd_val:.{4}g}"))
            table.setItem(i, 2, QTableWidgetItem(f"{rel_val:.{4}g}"))

        table.setVisible(nrow > 0)
        button.setVisible(nrow > 0)

    async def _computeForceCoeffsForCurrentCase(self, cfg: dict) -> dict:
        rname = cfg.get("region")
        boundaries_ids = cfg.get("boundaryIds")

        boundaries = [BoundaryDB.getBoundaryName(bcid) for bcid in boundaries_ids]

        db = CoreDBReader()

        aRef = float(db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + "/area"))
        lRef = float(db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + "/length"))
        magUInf = float(db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + "/velocity"))
        rhoInf = float(db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + "/density"))

        dragDir = cfg.get("dragDir") or [1.0, 0.0, 0.0]
        liftDir = cfg.get("liftDir") or [0.0, 1.0, 0.0]
        cofr = cfg.get("centerOfRotation") or [0.0, 0.0, 0.0]

        method = cfg.get("directionMethod")

        aoa = float(cfg.get("aoa", 0.0))
        aos = float(cfg.get("aos", 0.0))

        if method == DirectionSpecificationMethod.AOA_AOS:
            dragDir, liftDir = calucateDirectionsByRotation(
                dragDir, liftDir, aoa, aos
            )

        if GeneralDB.isDensityBased():
            pRef = None
        else:
            referencePressure = float(db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + "/pressure"))
            operatingPressure = float(db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + "/pressure"))
            pRef = referencePressure + operatingPressure

        seed = str(uuid.uuid4())
        coeffsFoName = f"delete_me_{seed}_coeffs"

        data = {
            "functions": {
                coeffsFoName: foForceCoeffsReport(
                    boundaries, aRef, lRef, magUInf, rhoInf,
                    dragDir, liftDir, cofr, pRef, rname
                )
            }
        }

        foDict = FoDict(f"delete_me_{seed}").build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()

        proc = await runParallelUtility(
            solver, "-postProcess", "-latestTime",
            "-dict", str(dictRelativePath),
            parallel=parallel.getEnvironment(),
            cwd=caseRoot
        )
        rc = await proc.wait()

        try:
            foDict.fullPath().unlink()
        except Exception:
            pass

        if rc != 0:
            raise RuntimeError("force coefficient postProcess failed")

        coeffsPath = FileSystem.postProcessingPath(rname or '') / coeffsFoName
        coeffsFiles = list(coeffsPath.glob("**/coefficient.dat"))

        if not coeffsFiles:
            utils.rmtree(coeffsPath, ignore_errors=True)
            raise RuntimeError("force coefficient result file(coefficient.dat) is not found.")

        df = readPostFile(coeffsFiles[0])

        try:
            cd_val = float(df["Cd"].iloc[-1])
            cl_val = float(df["Cl"].iloc[-1])
            cm_val = float(df["CmPitch"].iloc[-1])
        except Exception as e:
            utils.rmtree(coeffsPath, ignore_errors=True)
            raise RuntimeError(f"force coefficient result parsing failed: {e}")

        utils.rmtree(coeffsPath, ignore_errors=True)

        return {"Cd": cd_val, "Cl": cl_val, "Cm": cm_val}

    async def _computePointValueForCurrentCase(self, cfg: dict) -> float | None:
        coordinate = cfg.get("coordinate")
        field = cfg.get("field")
        fieldComponent = cfg.get("fieldComponent")
        snapOntoBoundary = cfg.get("snapOntoBoundary")

        rname = (cfg.get("region") or "").strip()

        seed = str(uuid.uuid4())
        foName = f'delete_me_{seed}_point'
        functions = {}
        solverFieldName = getSolverFieldName(field)

        if isinstance(field, CollateralField):
            time = FileSystem.latestTime()
            if FileSystem.fieldExists(time, solverFieldName):
                functions[f'readField_{solverFieldName}'] = foReadFieldsReport([solverFieldName], rname)  # FO for reading the collateral field
            else:
                functions.update(collateralFieldDict([field]))  # FO for generating the collateral field

        elif isinstance(field, SpecieField):
            if field.codeName not in RegionDB.getSecondaryMaterials(rname):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the material is configured does not contain selected surface."))
                return

        elif isinstance(field, UserScalarField):
            if rname != UserDefinedScalarsDB.getRegion(field.codeName):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the scalar field is configured does not contain selected surface."))
                return

        if field.type == FieldType.SCALAR:
            reportFieldName = solverFieldName

        else:  # FieldType.VECTOR
            if fieldComponent == VectorComponent.MAGNITUDE:
                functions['mag1'] = foMagReport(solverFieldName)
            else:
                functions['components1'] = foComponentsReport(solverFieldName)

            reportFieldName = getSolverComponentName(field, fieldComponent)

        if snapOntoBoundary:
            boundary = BoundaryDB.getBoundaryName(snapOntoBoundary)
            functions[foName] = foPatchProbesReport(boundary, reportFieldName, coordinate, rname)
        else:
            functions[foName] = foProbesReport(reportFieldName, coordinate, rname)

        data = {"functions": functions}

        fo_dict = FoDict(f"delete_me_{seed}").build(data)
        fo_dict.write()

        case_root = FileSystem.caseRoot()
        solver = findSolver()
        dict_rel_path = Path(os.path.relpath(fo_dict.fullPath(), case_root)).as_posix()

        try:
            proc = await runParallelUtility(
                solver,
                "-postProcess",
                "-latestTime",
                "-dict",
                str(dict_rel_path),
                parallel=parallel.getEnvironment(),
                cwd=case_root,
            )
            rc = await proc.wait()
        finally:
            try:
                fo_dict.fullPath().unlink()
            except Exception:
                logger.exception("ROM eval: failed to remove temporary point FoDict file")

        if rc != 0:
            logger.warning("ROM eval: point computation failed (rc=%s)", rc)
            return None

        fo_path = FileSystem.postProcessingPath(rname or "") / foName
        try:
            fo_files: list[Path] = list(fo_path.glob(f"**/{reportFieldName}"))
            if not fo_files:
                logger.warning(
                    "ROM eval: point probes output not found for field '%s' (path=%s)",
                    reportFieldName, fo_path,
                )
                return None

            df = readPostFile(fo_files[0])
            return float(df.iloc[0, 0])
        finally:
            try:
                utils.rmtree(fo_path)
            except Exception:
                logger.exception("ROM eval: failed to cleanup point postProcessing folder")

    async def _computeSurfaceFieldValueForCurrentCase(self, cfg: dict) -> float | None:
        surface = cfg.get("surface")
        reportType = cfg.get("reportType")
        field = cfg.get("field")
        fieldComponent = cfg.get("fieldComponent")

        rname = BoundaryDB.getBoundaryRegion(surface)

        seed = uuidToNnstr(uuid.uuid4())
        foName = f'delete_me_{seed}_surface'
        functions: dict[str, object] = {}

        if reportType == SurfaceReportType.MASS_FLOW_RATE:
            solverFieldName = 'phi'
            functions[foName] = foSurfaceFieldValueReport(BoundaryDB.getBoundaryName(surface), solverFieldName, reportType, rname)

        elif reportType == SurfaceReportType.VOLUME_FLOW_RATE:
            solverFieldName = 'U'
            functions[foName] = foSurfaceFieldValueReport(BoundaryDB.getBoundaryName(surface), solverFieldName, reportType, rname)

        else:
            solverFieldName = getSolverFieldName(field)

            if isinstance(field, CollateralField):
                time = FileSystem.latestTime()
                if FileSystem.fieldExists(time, solverFieldName):
                    functions[f'readField_{solverFieldName}'] = foReadFieldsReport([solverFieldName], rname)  # FO for reading the collateral field
                else:
                    functions.update(collateralFieldDict([field]))  # FO for generating the collateral field

            elif isinstance(field, SpecieField):
                if field.codeName not in RegionDB.getSecondaryMaterials(rname):
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr("The region where the material is configured does not contain selected surface."))
                    return

            elif isinstance(field, UserScalarField):
                if rname != UserDefinedScalarsDB.getRegion(field.codeName):
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr("The region where the scalar field is configured does not contain selected surface."))
                    return

            if field.type == FieldType.SCALAR:
                functions[foName] = foSurfaceFieldValueReport(BoundaryDB.getBoundaryName(surface), solverFieldName, reportType, rname)

            else:  # FieldType.VECTOR
                if fieldComponent == VectorComponent.MAGNITUDE:
                    functions['mag1'] = foMagReport(solverFieldName)
                else:
                    functions['components1'] = foComponentsReport(solverFieldName)

                solverComponentName = getSolverComponentName(field, fieldComponent)
                functions[foName] = foSurfaceFieldValueReport(BoundaryDB.getBoundaryName(surface), solverComponentName, reportType, rname)

        data = {"functions": functions}

        fo_dict = FoDict(f"delete_me_{seed}").build(data)
        fo_dict.write()

        case_root = FileSystem.caseRoot()
        solver = findSolver()
        dict_rel_path = Path(os.path.relpath(fo_dict.fullPath(), case_root)).as_posix()

        try:
            proc = await runParallelUtility(
                solver,
                "-postProcess",
                "-latestTime",
                "-dict",
                str(dict_rel_path),
                parallel=parallel.getEnvironment(),
                cwd=case_root,
            )
            rc = await proc.wait()
        finally:
            try:
                fo_dict.fullPath().unlink()
            except Exception:
                logger.exception("ROM eval: failed to remove temporary surface FoDict file")

        if rc != 0:
            logger.warning("ROM eval: surface computation failed (rc=%s)", rc)
            return None

        fo_path = FileSystem.postProcessingPath(rname or "") / foName
        try:
            fo_files: list[Path] = list(fo_path.glob("**/surfaceFieldValue.dat"))
            if not fo_files:
                logger.warning(
                    "ROM eval: surfaceFieldValue.dat not found (path=%s, surface=%d)",
                    fo_path, surface,
                )
                return None

            df = readPostFile(fo_files[0])
            return float(df.iloc[0, 0])
        finally:
            try:
                utils.rmtree(fo_path)
            except Exception:
                logger.exception("ROM eval: failed to cleanup surface postProcessing folder")

    async def _computeVolumeFieldValueForCurrentCase(self, cfg: dict) -> float | None:
        volume = cfg.get("volume")
        reportType = cfg.get("reportType")
        field = cfg.get("field")
        fieldComponent = cfg.get("fieldComponent")

        rname = CellZoneDB.getCellZoneRegion(volume)

        seed = uuidToNnstr(uuid.uuid4())
        foName = f'delete_me_{seed}_volume'
        functions: dict[str, object] = {}

        solverFieldName = getSolverFieldName(field)

        if isinstance(field, CollateralField):
            time = FileSystem.latestTime()
            if FileSystem.fieldExists(time, solverFieldName):
                functions[f'readField_{solverFieldName}'] = foReadFieldsReport([solverFieldName], rname)  # FO for reading the collateral field
            else:
                functions.update(collateralFieldDict([field]))  # FO for generating the collateral field

        elif isinstance(field, SpecieField):
            if field.codeName not in RegionDB.getSecondaryMaterials(rname):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the material is configured does not contain selected surface."))
                return

        elif isinstance(field, UserScalarField):
            if rname != UserDefinedScalarsDB.getRegion(field.codeName):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the scalar field is configured does not contain selected surface."))
                return

        name = CellZoneDB.getCellZoneName(volume)
        if CellZoneDB.isRegion(name):
            volumeType = VolumeType.All
            volumeName = None
        else:
            volumeType = VolumeType.CELLZONE
            volumeName = name

        if field.type == FieldType.SCALAR:
            functions[foName] = foVolFieldValueReport(volumeType, volumeName, solverFieldName, reportType, rname)

        else:  # FieldType.VECTOR
            if fieldComponent == VectorComponent.MAGNITUDE:
                functions['mag1'] = foMagReport(solverFieldName)
            else:
                functions['components1'] = foComponentsReport(solverFieldName)

            solverComponentName = getSolverComponentName(field, fieldComponent)
            functions[foName] = foVolFieldValueReport(volumeType, volumeName, solverComponentName, reportType, rname)

        data = {"functions": functions}

        fo_dict = FoDict(f"delete_me_{seed}").build(data)
        fo_dict.write()

        case_root = FileSystem.caseRoot()
        solver = findSolver()
        dict_rel_path = Path(os.path.relpath(fo_dict.fullPath(), case_root)).as_posix()

        try:
            proc = await runParallelUtility(
                solver,
                "-postProcess",
                "-latestTime",
                "-dict",
                str(dict_rel_path),
                parallel=parallel.getEnvironment(),
                cwd=case_root,
            )
            rc = await proc.wait()
        finally:
            try:
                fo_dict.fullPath().unlink()
            except Exception:
                logger.exception("ROM eval: failed to remove temporary volume FoDict file")

        if rc != 0:
            logger.warning("ROM eval: volume computation failed (rc=%s)", rc)
            return None

        fo_path = FileSystem.postProcessingPath(rname or "") / foName
        try:
            fo_files: list[Path] = list(fo_path.glob("**/volFieldValue.dat"))
            if not fo_files:
                logger.warning(
                    "ROM eval: volFieldValue.dat not found (path=%s, volume=%s)",
                    fo_path, volumeName,
                )
                return None

            df = readPostFile(fo_files[0])
            return float(df.iloc[0, 0])
        finally:
            try:
                utils.rmtree(fo_path)
            except Exception:
                logger.exception("ROM eval: failed to cleanup volume postProcessing folder")

    async def _computeEvalMetricsForCurrentCase(self, settings) -> list[dict]:
        items = settings.get("items", [])

        results: list[dict] = []

        for item in items:
            if not item.get("enabled", True):
                continue

            item_id = str(item.get("id") or "")
            category = item.get("category")
            cfg = item.get("config") or {}

            if category == "forceCoeff":
                metrics = cfg.get("metrics") or {}
                if not any(metrics.values()):
                    continue

                try:
                    coeffs = await self._computeForceCoeffsForCurrentCase(cfg)
                except Exception as e:
                    logger.exception("ROM eval: forceCoeff calculation failed: %s", e)
                    continue

                for key, enabled in metrics.items():
                    if not enabled:
                        continue

                    suffix = {
                        "lift": "Cl",
                        "drag": "Cd",
                        "moment": "Cm",
                    }.get(key, key)

                    label = f"{suffix}"

                    if key == "lift":
                        val = coeffs.get("Cl")
                    elif key == "drag":
                        val = coeffs.get("Cd")
                    elif key == "moment":
                        val = coeffs.get("Cm")
                    else:
                        val = None

                    if val is None:
                        continue

                    results.append({
                        "metricCategory": "forceCoeff",
                        "metricKey": f"{item_id}:{key}",
                        "metricLabel": label,
                        "value": float(val),
                    })

            elif category == "point":
                try:
                    val = await self._computePointValueForCurrentCase(cfg)
                except Exception:
                    logger.exception("ROM eval: point calculation failed (cfg=%s)", cfg)
                    continue

                if val is None:
                    continue

                results.append({
                    "metricCategory": "point",
                    "metricKey": item_id,
                    "metricLabel": "P",
                    "value": float(val),
                })

            # --- surface ---
            elif category == "surface":
                try:
                    val = await self._computeSurfaceFieldValueForCurrentCase(cfg)
                except Exception:
                    logger.exception("ROM eval: surface calculation failed (cfg=%s)", cfg)
                    continue

                if val is None:
                    continue

                results.append({
                    "metricCategory": "surface",
                    "metricKey": item_id,
                    "metricLabel": "S",
                    "value": float(val),
                })

            # --- volume ---
            elif category == "volume":
                try:
                    val = await self._computeVolumeFieldValueForCurrentCase(cfg)
                except Exception:
                    logger.exception("ROM eval: volume calculation failed (cfg=%s)", cfg)
                    continue

                if val is None:
                    continue

                results.append({
                    "metricCategory": "volume",
                    "metricKey": item_id,
                    "metricLabel": "V",
                    "value": float(val),
                })

            else:
                logger.warning("ROM eval: unknown metric category '%s'", category)
                continue

        return results

    async def _evalRomCfdEvaluationForCase(self, caseName: str, paramsAll: dict,
                                           settings, enhanceIndex: int,
                                           progressDialog: ProgressDialog) -> list[dict]:
        progressDialog.setLabelText(
            self.tr(f"ROM Enhancement: evaluating ROM for {caseName} ({enhanceIndex+1})")
        )
        rom_metrics = await self._computeEvalMetricsForCurrentCase(settings)

        rom_map = {
            (m["metricCategory"], m["metricKey"], m["metricLabel"]): m["value"]
            for m in rom_metrics
        }

        progressDialog.setLabelText(
            self.tr(f"ROM Enhancement: running CFD case {caseName} ({enhanceIndex+1})")
        )
        runParams = {k: str(v) for k, v in paramsAll.items()}
        await self._caseManager.batchRun([BatchCase(caseName, runParams)])

        progressDialog.setLabelText(
            self.tr(f"ROM Enhancement: evaluating CFD for {caseName} ({enhanceIndex+1})")
        )
        cfd_metrics = await self._computeEvalMetricsForCurrentCase(settings)

        rows = []

        for m in cfd_metrics:
            key = (m["metricCategory"], m["metricKey"], m["metricLabel"])
            cfd_val = float(m["value"])
            rom_val = float(rom_map.get(key, 0.0))

            if cfd_val != 0.0:
                rel_err = abs(cfd_val - rom_val) / abs(cfd_val) * 100.0
            else:
                rel_err = 0.0

            label = f"{caseName}/{m['metricLabel']}"

            rows.append({
                "case": caseName,
                "metricLabel": label,
                "metricCategory": m["metricCategory"],
                "metricKey": m["metricKey"],
                "rom": rom_val,
                "cfd": cfd_val,
                "relErrPercent": rel_err,
            })

        return rows

    def _storeEvalResults(self, rows):
        if not rows:
            return

        df = pd.DataFrame(rows)

        self._project.fileDB().putDataFrame(ROM_EVAL_RESULTS_KEY, df)
        self._updateEvalResultTableFromDataFrame(df)

    @qasync.asyncSlot()
    async def _EvalNEnhanceROM(self, num, evalSettings):
        ROMdate = self._project.fileDB().getText("ROMdate")
        if not ROMdate:
            await AsyncMessageBox().warning(
                self, self.tr('Reduced Order Model'),
                self.tr('ROM must be built before enhancement.')
            )
            return

        if GeneralDB.isTimeTransient():
            confirm = await AsyncMessageBox().question(
                self, self.tr('Outdated ROM'),
                self.tr('The current ROM model is an outdated version based on steady simulation results. Continue?')
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        progressDialog = ProgressDialog(self, self.tr('Reduced Order Model'), cancelable=True)
        self._caseManager.progress.connect(progressDialog.setLabelText)
        progressDialog.setLabelText(self.tr('ROM Enhancement: initializing'))
        progressDialog.cancelClicked.connect(self._caseManager.cancel)
        progressDialog.open()

        allEvalRows = []

        try:
            self._snapshotCaseList.clear()
            self._snapshotCaseList.load()

            listParam = self._snapshotCaseList.parameters().tolist() if self._snapshotCaseList.parameters() is not None else []

            if not listParam:
                raise RuntimeError("No parameters found in snapshot case list.")

            activeNames = self._project.fileDB().getText("ROMparams").decode("utf-8").split("\n")
            self._paramActive = {name: True for name in activeNames}

            for iEnh in range(num):
                progressDialog.setLabelText(
                    self.tr(f'ROM Enhancement: selecting sample {iEnh+1}/{num}')
                )

                self._snapshotCaseList.clear()
                self._snapshotCaseList.load()
                listSnapshotCase = self._snapshotCaseList._cases

                if not listSnapshotCase:
                    raise RuntimeError("No snapshot cases loaded during ROM enhancement.")

                candidateActive = self._pickAdditionalSampleSimpleGP(activeNames)

                inferredInactive = self._inferInactiveParamsLinear(
                    listSnapshotCase=listSnapshotCase,
                    allParams=listParam,
                    activeMask=self._paramActive,
                    userActiveValues=candidateActive
                )

                paramsAll = {}
                for k, v in candidateActive.items():
                    paramsAll[k] = float(v)
                for k, v in inferredInactive.items():
                    paramsAll[k] = float(v)

                caseName = self._nextEnhancementCaseName()

                progressDialog.setLabelText(
                    self.tr(f'ROM Enhancement: reconstructing {caseName} ({iEnh+1}/{num})')
                )

                paramsActive = {p: paramsAll[p] for p in activeNames if p in paramsAll}

                await self._caseManager.podInitReconstructedCase(caseName, paramsAll)
                await self._caseManager.podRunReconstruct(caseName, listSnapshotCase, paramsActive, isBatchRunning=True)
                await self._caseManager.podSaveToBatchCase(caseName)
                await self._caseManager.podAddToBatchList(caseName, paramsAll)

                caseEvalRows = await self._evalRomCfdEvaluationForCase(
                    caseName=caseName,
                    paramsAll=paramsAll,
                    settings=evalSettings,
                    enhanceIndex=iEnh,
                    progressDialog=progressDialog
                )
                allEvalRows.extend(caseEvalRows)

                snapshotDF = self._project.fileDB().getDataFrame(FileDB.Key.SNAPSHOT_CASES.value)
                if snapshotDF is None:
                    import pandas as pd
                    snapshotDF = pd.DataFrame(columns=listParam)

                row = {}
                for p in snapshotDF.columns:
                    val = paramsAll.get(p, "")
                    row[p] = str(val)
                snapshotDF.loc[caseName] = row
                self._project.fileDB().putDataFrame(FileDB.Key.SNAPSHOT_CASES.value, snapshotDF)

                progressDialog.setLabelText(
                    self.tr(f'ROM Enhancement: rebuilding ROM ({iEnh+1}/{num})')
                )
                listSnapshotNames = snapshotDF.index.astype(str).tolist()
                await self._caseManager.podRunGenerateROM(listSnapshotNames, isBatchRunning=True)

                ROMdate = time.strftime("%Y-%m-%d, %H:%M:%S", time.localtime())
                ROMaccuracy = self._caseManager.podGetROMAccuracy()
                self._project.fileDB().putText("ROMdate", ROMdate)
                self._project.fileDB().putText("ROMaccuracy", ROMaccuracy)
                self._project.fileDB().putText("ROMparams", "\n".join(activeNames))

            if allEvalRows:
                self._storeEvalResults(allEvalRows)

            self.loadSnapshotCases(overwriteSlider=True)
            progressDialog.finish(self.tr('ROM enhancement finished'))

        except Exception as e:
            logging.exception("ROM enhancement error")
            progressDialog.finish(self.tr('ROM enhancement error : ') + str(e))
        finally:
            try:
                self._caseManager.progress.disconnect(progressDialog.setLabelText)
            except Exception:
                pass

    def _pickAdditionalSampleSimpleGP(self, activeParams, nCandidates=512):
        snapshotCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.SNAPSHOT_CASES.value)
        if snapshotCasesDataFrame is None or snapshotCasesDataFrame.empty:
            raise RuntimeError("No snapshot cases available for ROM enhancement.")

        cols = [p for p in activeParams if p in snapshotCasesDataFrame.columns]
        if not cols:
            raise RuntimeError("No active parameters found in SNAPSHOT_CASES dataframe.")

        X_train = snapshotCasesDataFrame[cols].astype(float).to_numpy()
        nTrain, dim = X_train.shape

        if nTrain < 2:
            raise RuntimeError("Edge point tbd")

        mins = X_train.min(axis=0)
        maxs = X_train.max(axis=0)
        ranges = maxs - mins
        ranges[ranges <= 0.0] = 1.0

        length_scale = ranges/nTrain
        sigma_f2 = 1.0
        sigma_n2 = 1e-6

        def kernel(a, b):
            """
            a: (Na, d), b: (Nb, d) -> (Na, Nb)
            """
            diff = a[:, None, :] - b[None, :, :]
            scaled = diff / length_scale
            sqdist = np.sum(scaled * scaled, axis=2)
            return sigma_f2 * np.exp(-0.5 * sqdist)

        K = kernel(X_train, X_train)
        idx = np.diag_indices_from(K)
        K[idx] += sigma_n2

        use_inv = False
        try:
            L = np.linalg.cholesky(K)
        except np.linalg.LinAlgError:
            K_inv = np.linalg.pinv(K)
            use_inv = True

        nCandidates = int(max(4 * max(dim, 1) * max(dim, 1), nCandidates))
        nCandidates = min(nCandidates, 2048)
        rng = np.random.default_rng()
        rand = rng.random(size=(nCandidates, dim))
        candidates = mins + rand * (maxs - mins)

        best_idx = 0
        best_var = -1.0

        for i in range(nCandidates):
            x_star = candidates[i:i+1, :]      # (1, d)
            k_star = kernel(X_train, x_star)   # (N, 1)
            k_star = k_star[:, 0]              # (N,)

            if use_inv:
                v = K_inv @ k_star
            else:
                y = np.linalg.solve(L, k_star)
                v = np.linalg.solve(L.T, y)

            k_ss = sigma_f2
            var = max(0.0, float(k_ss - k_star.dot(v)))

            if var > best_var:
                best_var = var
                best_idx = i

        x_best = candidates[best_idx]
        return {p: float(x_best[i]) for i, p in enumerate(cols)}

    def _nextEnhancementCaseName(self):
        batchCasesDataFrame = self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value)
        maxIdx = -1

        if batchCasesDataFrame is not None and not batchCasesDataFrame.empty:
            for name in batchCasesDataFrame.index.astype(str).tolist():
                m = re.match(r"case_(\d+)$", name)
                if not m:
                    continue
                idx = int(m.group(1))
                if idx > maxIdx:
                    maxIdx = idx

        return f"case_{maxIdx+1:04d}"

    @qasync.asyncSlot()
    async def _openExportDialog(self):
        self._dialog = QFileDialog(self, self.tr('Export Evaluation Result'), '', self.tr('Excel (*.xlsx);; CSV (*.csv)'))
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.fileSelected.connect(self._exportEvaluationResult)
        self._dialog.open()

    def _exportEvaluationResult(self, file):
        df = self._project.fileDB().getDataFrame(ROM_EVAL_RESULTS_KEY)
        if df is None or df.empty:
            AsyncMessageBox().warning(self, self.tr("Export"), self.tr("No evaluation results to export."))
            return

        out = df.copy()

        if "case" in out.columns:
            out = out.set_index("case")

        if file.lower().endswith('xlsx'):
            out.to_excel(file, index_label='Case Name')
        else:
            out.to_csv(file, sep=',', index_label='Case Name')

    def closeEvent(self, event):
        self._disconnectSignalsSlots()
        self._snapshotCaseList.close()

        super().closeEvent(event)