#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal

from baramSnappy.db.configurations_schema import Step


steps = {
    'geometryStep': Step.GEOMETRY,
    'baseGridStep': Step.BASE_GRID,
    'regionStep': Step.REGION,
    'castellationStep': Step.CASTELLATION,
    'snapStep': Step.SNAP,
    'boundaryLayerStep': Step.BOUNDARY_LAYER,
    'exportStep': Step.EXPORT
}


class NavigationView(QObject):
    currentStepChanged = Signal(int, int)

    def __init__(self, buttons):
        super().__init__()
        self._steps = buttons
        self._currentStep = None

        for b in self._steps.buttons():
            self._steps.setId(b, steps[b.objectName()])

        self._connectSignalsSlots()

    def currentStep(self):
        return self._currentStep

    def setCurrentStep(self, step):
        self._steps.button(step).setChecked(True)
        self._stepChanged(step)

    def enableStep(self, step):
        self._steps.button(step).setEnabled(True)

    def disableStep(self, step):
        self._steps.button(step).setEnabled(False)

    def _connectSignalsSlots(self):
        self._steps.idClicked.connect(self._stepChanged)

    def _stepChanged(self, step=None):
        step = self._steps.id(self._steps.checkedButton())
        self.currentStepChanged.emit(step, self._currentStep)
        self._currentStep = step


