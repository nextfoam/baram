#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal

from baramMesh.db.configurations_schema import Step


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

    def __init__(self, ui):
        super().__init__()

        self._ui = ui
        self._steps = ui.stepButtons
        self._currentStep = Step.NONE
        self._workingStep = Step.GEOMETRY

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
        self._updateBatchStepsEnabled()

    def disableStep(self, step):
        if step != Step.SNAP and step != Step.BOUNDARY_LAYER:
            self._steps.button(step).setEnabled(False)

        self._updateBatchStepsEnabled()

    def setWorkingStep(self, step):
        def setBold(button, bold):
            font = button.font()
            font.setBold(bold)
            button.setFont(font)

        self.enableStep(step)
        setBold(self._steps.button(self._workingStep), False)
        self._workingStep = step
        setBold(self._steps.button(step), True)

    def _connectSignalsSlots(self):
        self._steps.idClicked.connect(self._stepChanged)

    def _stepChanged(self, step=None):
        step = self._steps.id(self._steps.checkedButton())
        self.currentStepChanged.emit(step, self._currentStep)
        self._currentStep = step

    def _updateBatchStepsEnabled(self):
        self._ui.snapStep.setEnabled(self._ui.castellationStep.isEnabled())
        self._ui.boundaryLayerStep.setEnabled(self._ui.castellationStep.isEnabled())
