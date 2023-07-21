#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class NavigationView(QObject):
    stepSelected = Signal(int)

    def __init__(self, view):
        super().__init__()
        self._view = view
        self._openedStep = None
        self._currentStep = None

        self._connectSignalsSlots()

    def currentStep(self):
        return self._currentStep

    def enableStep(self, step):
        self._view.topLevelItem(step).setDisabled(False)

    def setOpenedStep(self, step):
        self._openedStep = step
        self._view.topLevelItem(step).setDisabled(False)
        self._view.setCurrentItem(self._view.topLevelItem(step))
        self._setCurrentStep(self._openedStep)

    def isOpenedStep(self, step):
        return step == self._openedStep

    def openNextStep(self):
        self._openedStep = self._currentStep + 1
        self._view.topLevelItem(self._openedStep).setDisabled(False)
        self._setCurrentStep(self._openedStep)

        return self._openedStep

    def unlockCurrentStep(self):
        for i in range(self._currentStep + 1, self._openedStep + 1):
            self._view.topLevelItem(i).setDisabled(True)

        self._openedStep = self._currentStep

    def _setCurrentStep(self, step):
        if step > self._openedStep:
            return

        self._view.setCurrentItem(self._view.topLevelItem(step))

    def _connectSignalsSlots(self):
        self._view.itemSelectionChanged.connect(self._stepSelected)

    def _stepSelected(self):
        self._currentStep = self._view.indexOfTopLevelItem(self._view.currentItem())
        self.stepSelected.emit(self._currentStep)


