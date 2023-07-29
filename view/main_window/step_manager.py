#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .main_window_ui import Ui_MainWindow

from app import app
from db.configurations_schema import Step
from .step import GeometryStep, BaseGridStep, CastellationStep


steps = {
    Step.GEOMETRY.value: GeometryStep(),
    Step.BASE_GRID.value: BaseGridStep(),
    Step.CASTELLATION.value: CastellationStep(),
    Step.SNAP.value: None,
    Step.BOUNDARY_LAYER.value: None,
    Step.REFINEMENT.value: None,
}


class StepControlButtons:
    def __init__(self, ui):
        self._next = ui.next
        self._unlock = ui.unlock

    @property
    def nextButton(self):
        return self._next

    @property
    def unlockButton(self):
        return self._unlock

    def setToOpenedMode(self):
        self._next.show()
        self._unlock.hide()

    def setToLockedMode(self):
        self._next.hide()
        self._unlock.show()

    def setNextEnabled(self, enabled):
        self._next.setEnabled(enabled)


class StepManager:
    def __init__(self, navigation, ui:Ui_MainWindow):
        self._navigation = navigation
        self._openedStep = None
        self._contentStack = ui.content
        self._buttons = StepControlButtons(ui)
        self._contentPages = {}

        self._connectSignalsSlots()

    def load(self):
        step = app.db.getEnumValue('step')
        self._openedStep = step

        for s in range(step):
            if self.isStepCompleted(s):
                self._navigation.enableStep(s)
            else:
                step = s
                break

        self._setOpenedStep(step)
        self._navigation.setCurrentStep(self._openedStep)

    def isOpenedStep(self, step):
        return step == self._openedStep

    def isStepCompleted(self, step):
        return steps[step].isNextStepAvailable()

    def openNextStep(self):
        step = self._navigation.currentStep() + 1
        steps[step].clearResult()
        self._setOpenedStep(step)
        self._navigation.setCurrentStep(self._openedStep)

    def _connectSignalsSlots(self):
        self._navigation.currentStepChanged.connect(self._moveToStep)
        self._buttons.nextButton.clicked.connect(self.openNextStep)
        self._buttons.unlockButton.clicked.connect(self._unlockCurrentStep)

    def _setOpenedStep(self, step):
        self._navigation.enableStep(step)
        self._openedStep = step

        db = app.db.checkout()
        db.setValue('step', step)
        app.db.commit(db)

    def _moveToStep(self, step):
        page = steps[step].page()
        if page is None:
            page = steps[step].createPage()
            self._contentStack.addWidget(page)

        self._contentStack.setCurrentWidget(page)

        if self.isOpenedStep(step):
            self._buttons.setToOpenedMode()
            self._buttons.setNextEnabled(self.isStepCompleted(step))
        else:
            page.lock()
            self._buttons.setToLockedMode()

    def _unlockCurrentStep(self):
        currentStep = self._navigation.currentStep()
        self._resetSteps(currentStep)

        app.window.meshManager.clear()

        self._setOpenedStep(currentStep)
        steps[currentStep].page().unlock()

        self._buttons.nextButton.setEnabled(True)
        self._buttons.setToOpenedMode()

    def _resetSteps(self, baseStep):
        for step in range(baseStep, self._openedStep + 1):
            self._navigation.disableStep(step)
            steps[step].clearResult()
