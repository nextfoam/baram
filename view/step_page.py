#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

from app import app
from libbaram.utils import rmtree


class StepPage(QObject):
    OUTPUT_TIME = -1

    def __init__(self, ui, page):
        super().__init__()
        self._ui = ui
        self._widget = page

    def isNextStepAvailable(self):
        return app.fileSystem.timePath(self.OUTPUT_TIME).exists()

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
        path = app.fileSystem.timePath(self.OUTPUT_TIME)
        if path.exists():
            rmtree(path)

        for path in app.fileSystem.caseRoot().glob(f'processor*/{self.OUTPUT_TIME}'):
            rmtree(path)

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
