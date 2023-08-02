#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class NavigationView(QObject):
    currentStepChanged = Signal(int, int)

    def __init__(self, view):
        super().__init__()
        self._view = view

        self._connectSignalsSlots()

    def currentStep(self):
        return self._view.indexOfTopLevelItem(self._view.currentItem())

    def setCurrentStep(self, step):
        self._view.setCurrentItem(self._view.topLevelItem(step))

    def enableStep(self, step):
        self._view.topLevelItem(step).setDisabled(False)

    def disableStep(self, step):
        self._view.topLevelItem(step).setDisabled(True)

    def _connectSignalsSlots(self):
        self._view.currentItemChanged.connect(self._stepSelected)

    def _stepSelected(self, current, previous):
        self.currentStepChanged.emit(self._view.indexOfTopLevelItem(current), self._view.indexOfTopLevelItem(previous))


