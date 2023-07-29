#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class NavigationView(QObject):
    currentStepChanged = Signal(int)

    def __init__(self, view):
        super().__init__()
        self._view = view
        self._currentStep = None

        self._connectSignalsSlots()

    def currentStep(self):
        return self._currentStep

    def setCurrentStep(self, step):
        self._view.setCurrentItem(self._view.topLevelItem(step))
        self._currentStep = step

    def enableStep(self, step):
        self._view.topLevelItem(step).setDisabled(False)

    def disableStep(self, step):
        self._view.topLevelItem(step).setDisabled(True)

    def _connectSignalsSlots(self):
        self._view.itemSelectionChanged.connect(self._stepSelected)

    def _stepSelected(self):
        self._currentStep = self._view.indexOfTopLevelItem(self._view.currentItem())
        self.currentStepChanged.emit(self._currentStep)


