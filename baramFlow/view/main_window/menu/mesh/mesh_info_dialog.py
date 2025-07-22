#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio

from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QDialog, QApplication

from baramFlow.app import app
from baramFlow.mesh.mesh_model import MeshModel
from .mesh_info_dialog_ui import Ui_MeshInfoDialog


class MeshInfoDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._proc = None
        self._task = None

        self._ui = Ui_MeshInfoDialog()
        self._ui.setupUi(self)

        self._task = asyncio.create_task(self._updateValues())

    async def _updateValues(self):
        QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))

        try:
            mesh: MeshModel = app.meshModel()

            xMin, xMax, yMin, yMax, zMin, zMax = await mesh.getBounds()

            xLen = xMax - xMin
            yLen = yMax - yMin
            zLen = zMax - zMin

            numCell = await mesh.getNumberOfCells()
            largestVolume = await mesh.getLargestCellVolume()
            smallestVolume = await mesh.getSmallestCellVolume()

            self._ui.xMin.setText(f'{xMin:.6g}')
            self._ui.xMax.setText(f'{xMax:.6g}')
            self._ui.xLen.setText(f'{xLen:.6g}')
            self._ui.yMin.setText(f'{yMin:.6g}')
            self._ui.yMax.setText(f'{yMax:.6g}')
            self._ui.yLen.setText(f'{yLen:.6g}')
            self._ui.zMin.setText(f'{zMin:.6g}')
            self._ui.zMax.setText(f'{zMax:.6g}')
            self._ui.zLen.setText(f'{zLen:.6g}')

            self._ui.numCells.setText(f'{numCell:,}')
            self._ui.largestVolume.setText(f'{largestVolume:.6g}')
            self._ui.smallestVolume.setText(f'{smallestVolume:.6g}')

            self._ui.buttonOk.setEnabled(True)

        except asyncio.CancelledError:
            raise asyncio.CancelledError

        finally:
            QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        self._task.cancel()
        super().closeEvent(event)
