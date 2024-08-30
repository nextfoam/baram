#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import qasync
from PySide6.QtCore import QObject

from libbaram.utils import rmtree

from baramMesh.app import app
from baramMesh.openfoam.file_system import makeDir
from baramMesh.view.main_window.main_window_ui import Ui_MainWindow


class StepPage(QObject):
    OUTPUT_TIME = -1

    def __init__(self, ui, page):
        super().__init__()
        self._ui: Ui_MainWindow = ui
        self._widget = page
        self._loaded = False
        self._locked = False

    def isNextStepAvailable(self):
        return app.fileSystem.timePathExists(self.OUTPUT_TIME, app.project.parallelCores() > 1)

    def lock(self):
        self._disableStep()
        self._locked = True

    def unlock(self):
        self._enableStep()
        self._locked = False

    def open(self):
        return

    async def selected(self):
        self.updateMesh()

    def deselected(self):
        return

    @qasync.asyncSlot()
    async def save(self):
        return True

    def unload(self):
        self._loaded = False
        self._locked = False
        self._clear()

    def retranslate(self):
        return

    def clearResult(self):
        path = self._outputPath()
        if path and path.exists():
            rmtree(path)

        if self.OUTPUT_TIME < 1:
            processorPaths = app.fileSystem.caseRoot().glob(f'processor*')
        else:
            processorPaths = app.fileSystem.caseRoot().glob(f'processor*/{self.OUTPUT_TIME}')

        for path in processorPaths:
            rmtree(path)

    def createOutputPath(self):
        output = str(self.OUTPUT_TIME)

        if app.project.parallelCores() > 1:
            folders = app.fileSystem.processorFolders()
            if folders:
                for f in folders:
                    makeDir(f, output, True)

                return

        makeDir(app.fileSystem.caseRoot(), output, True)

    def _outputPath(self) -> Path:
        return app.fileSystem.timePath(self.OUTPUT_TIME)

    def _setNextStepEnabled(self, enabled):
        self._ui.next.setEnabled(enabled)

    def _updateNextStepAvailable(self):
        self._setNextStepEnabled(self.isNextStepAvailable())

    def _showResultMesh(self):
        app.window.meshManager.show(self.OUTPUT_TIME)

    def _showPreviousMesh(self):
        app.window.meshManager.show(self.OUTPUT_TIME - 1)

    def updateMesh(self):
        if self.isNextStepAvailable():
            self._showResultMesh()
        else:
            self._showPreviousMesh()

    def _disableControlsForRunning(self):
        self._ui.menuFile.setEnabled(False)
        self._ui.menuMesh_Quality.setEnabled(False)
        self._ui.menuParallel.setEnabled(False)

    def _enableControlsForSettings(self):
        self._ui.menuFile.setEnabled(True)
        self._ui.menuMesh_Quality.setEnabled(True)
        self._ui.menuParallel.setEnabled(True)

    def _enableStep(self):
        self._widget.setEnabled(True)

    def _disableStep(self):
        self._widget.setEnabled(False)

    def _clear(self):
        return
