#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from itertools import product
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
import qasync

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QTableWidgetItem, QComboBox, QCheckBox, QMessageBox

from widgets.async_message_box import AsyncMessageBox

from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .doe_dialog_ui import Ui_DoEDialog


class DoEDialog(ResizableDialog):
    samplesGenerated = Signal(pd.DataFrame)

    def __init__(self, parent, userParams: Dict[str, Dict[str, Any]], maxDoeIndex: int):
        super().__init__(parent)
        self._ui = Ui_DoEDialog()
        self._ui.setupUi(self)

        self._userParams = userParams
        self._maxDoeIndex = maxDoeIndex
        self._resultDF: Optional[pd.DataFrame] = None

        self._populateVariablesTable()
        self._connectSignalsSlots()

        self._ui.rbLHS.setChecked(True)
        self._updateStack()

    def isClearChecked(self):
        return self._ui.clearOldCases.isChecked()

    @qasync.asyncSlot()
    async def accept(self):
        try:
            rows = self._readTable()
            if self._ui.rbFullFact.isChecked():
                df = self._genFullFactorial(rows)
            elif self._ui.rbSobol.isChecked():
                df = self._genSobol(rows, self._ui.spnSamples.value())
            else:
                df = self._genLHS(rows, self._ui.spnSamples.value(), maximin_restarts=50)

            if "Case Name" not in df.columns:
                startIndex = 0
                if not self.isClearChecked() and self._maxDoeIndex >= 0:
                    startIndex = self._maxDoeIndex + 1

                df.insert(0, "Case Name",
                          [f"case_{i + startIndex:04d}" for i in range(len(df))])

            df.set_index("Case Name", inplace=True)

            df = df.astype(str)
            self._resultDF = df
            self.samplesGenerated.emit(df)
            super().accept()
        except Exception as e:
            await AsyncMessageBox().information(self, self.tr("Generate Samples"), f"Failed: {e}")

    def _connectSignalsSlots(self):
        self._ui.rbLHS.toggled.connect(self._updateStack)
        self._ui.rbSobol.toggled.connect(self._updateStack)
        self._ui.rbFullFact.toggled.connect(self._updateStack)

        self._ui.spnSamples.valueChanged.connect(self._refreshPreview)
        self._ui.tblVars.itemChanged.connect(self._refreshPreview)

        self._ui.buttonBox.accepted.connect(self.accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    def _updateStack(self):
        isFullFactorial = self._ui.rbFullFact.isChecked()

        if isFullFactorial:
            self._ui.stackMethod.setCurrentWidget(self._ui.pageFullFact)
        else:
            self._ui.stackMethod.setCurrentWidget(self._ui.pageSpaceFilling)

        tbl = self._ui.tblVars
        tbl.setColumnHidden(3, not isFullFactorial)

        self._refreshPreview()

    def _populateVariablesTable(self):
        tbl = self._ui.tblVars
        names = list(self._userParams.keys())

        tbl.setRowCount(len(names))
        tbl.setHorizontalHeaderLabels(["Name", "Min", "Max", "Levels", "Scale"])
        tbl.verticalHeader().setVisible(False)

        for r, name in enumerate(names):
            it_name = QTableWidgetItem(name)
            it_name.setFlags(it_name.flags() ^ Qt.ItemIsEditable)
            tbl.setItem(r, 0, it_name)

            v = self._userParams.get(name, {}).get("value", 0.0)
            for c, val in [(1, v), (2, v)]:
                tbl.setItem(r, c, QTableWidgetItem(str(val)))

            tbl.setItem(r, 3, QTableWidgetItem("3"))

            comboScale = QComboBox()
            comboScale.addItems(["linear", "log"])
            comboScale.currentIndexChanged.connect(self._refreshPreview)
            tbl.setCellWidget(r, 4, comboScale)

        tbl.resizeColumnsToContents()

    def _readTable(self) -> List[Dict[str, Any]]:
        tbl = self._ui.tblVars
        rows = []
        for r in range(tbl.rowCount()):
            name = tbl.item(r, 0).text()
            vmin = float(tbl.item(r, 1).text())
            vmax = float(tbl.item(r, 2).text())
            levels = int(tbl.item(r, 3).text()) if tbl.item(r, 3) else 3
            scale = tbl.cellWidget(r, 4).currentText()
            rows.append(dict(name=name, vmin=vmin, vmax=vmax,
                             levels=levels, scale=scale))
        return rows

    def _refreshPreview(self):
        try:
            rows = self._readTable()
            if self._ui.rbFullFact.isChecked():
                df = self._genFullFactorial(rows)
            elif self._ui.rbSobol.isChecked():
                df = self._genSobol(rows, self._ui.spnSamples.value())
            else:
                df = self._genLHS(rows, self._ui.spnSamples.value(), maximin_restarts=20)
            self._ui.txtPreview.setPlainText(df.to_string(index=False))
        except Exception as e:
            self._ui.txtPreview.setPlainText(f"(preview error) {e}")

    @staticmethod
    def _latinSimple(n: int, d: int, rng: np.random.Generator) -> np.ndarray:
        X = np.empty((n, d))
        for j in range(d):
            perm = rng.permutation(n)
            X[:, j] = (perm + rng.random(n)) / n
        return X

    @staticmethod
    def _pairwiseMinDist(X: np.ndarray) -> float:
        md = math.inf
        for i in range(X.shape[0] - 1):
            di = np.linalg.norm(X[i+1:] - X[i], axis=1).min()
            if di < md:
                md = di
        return md

    def _genLHS(self, rows: List[Dict[str, Any]], n: int, maximin_restarts=20) -> pd.DataFrame:
        D = len(rows)

        rng = np.random.default_rng(42)
        bestX, bestScore = None, -1.0
        for _ in range(max(1, maximin_restarts)):
            X = self._latinSimple(n, D, rng)
            score = self._pairwiseMinDist(X)
            if score > bestScore:
                bestScore, bestX = score, X
        U = bestX

        cols = self._scaleColumnsFromUnit(U, rows)
        return pd.DataFrame(cols)

    def _genSobol(self, rows: List[Dict[str, Any]], n: int) -> pd.DataFrame:
        D = len(rows)

        U = self._halton(n, D)

        cols = self._scaleColumnsFromUnit(U, rows)
        return pd.DataFrame(cols)

    def _scaleColumnsFromUnit(self, U: np.ndarray, rows):
        cols = {}
        for i, r in enumerate(rows):
            a, b = r["vmin"], r["vmax"]
            if r["scale"] == "log":
                a, b = math.log(a), math.log(b)
                vals = np.exp(a + (b - a) * U[:, i])
            else:
                vals = a + (b - a) * U[:, i]
            cols[r["name"]] = vals
        return cols

    @staticmethod
    def _vdcorput(n: int, base: int) -> np.ndarray:
        seq = np.zeros(n)
        for i in range(n):
            x, denom, idx = 0.0, 1.0, i + 1
            while idx > 0:
                idx, rem = divmod(idx, base)
                denom *= base
                x += rem / denom
            seq[i] = x
        return seq

    def _halton(self, n: int, d: int) -> np.ndarray:
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        assert d <= len(primes)
        cols = [self._vdcorput(n, primes[j]) for j in range(d)]
        return np.stack(cols, axis=1)

    def _genFullFactorial(self, rows: List[Dict[str, Any]]) -> pd.DataFrame:
        grids: List[List[Any]] = []
        names: List[str] = []
        for r in rows:
            names.append(r["name"])
            L = max(1, r["levels"])
            if r["scale"] == "log":
                a, b = math.log(r["vmin"]), math.log(r["vmax"])
                vals = np.exp(np.linspace(a, b, L))
            else:
                vals = np.linspace(r["vmin"], r["vmax"], L)
            grids.append(list(vals))

        combos = list(product(*grids))
        return pd.DataFrame(combos, columns=names)
