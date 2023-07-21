#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class StepPage(QWidget):
    nextStepAvailableChanged = Signal(bool)

    def __init__(self):
        super().__init__()

    @classmethod
    def nextStepAvailable(cls):
        return False

    def lock(self):
        self.setEnabled(False)

    def unlock(self):
        self.setEnabled(True)

    def clearResult(self):
        return

    def _updateNextStepAvailable(self):
        self.nextStepAvailableChanged.emit(self.nextStepAvailable())
