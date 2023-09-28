#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtCore import QObject

from libbaram.utils import rmtree

from baramSnappy.app import app
from baramSnappy.openfoam.file_system import makeDir


class StepPage(QObject):
    OUTPUT_TIME = -1

    def __init__(self, ui, page):
        super().__init__()
        self._ui = ui
        self._widget = page

    def isNextStepAvailable(self):
        return app.fileSystem.timePathExists(self.OUTPUT_TIME, app.project.parallelCores() > 1)

    def lock(self):
        self._widget.setEnabled(False)

    def unlock(self):
        self._widget.setEnabled(True)

    def open(self):
        return

    def selected(self):
        self._updateMesh()

    def deselected(self):
        return

    def save(self):
        return True

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

    def _updateMesh(self):
        if self.isNextStepAvailable():
            self._showResultMesh()
        else:
            self._showPreviousMesh()
