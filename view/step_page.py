#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from app import app


class StepPage(QWidget):
    nextStepAvailableChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self._updateNextStepAvailable()

    def lock(self):
        self.setEnabled(False)

    def unlock(self):
        self.setEnabled(True)

    def _updateNextStepAvailable(self):
        app.window.updateNextButtonEnabled()
