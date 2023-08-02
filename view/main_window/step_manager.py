#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .main_window_ui import Ui_MainWindow

from app import app
from db.configurations_schema import Step
from view.step_page import StepPage
from view.geometry.geometry_page import GeometryPage
from view.base_grid.base_grid_page import BaseGridPage
from view.castellation.castellation_page import CastellationPage
from view.snap.snap_page import SnapPage


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

        self._pages = {
            Step.NONE: StepPage(ui, None),
            Step.GEOMETRY: GeometryPage(ui),
            Step.BASE_GRID: BaseGridPage(ui),
            Step.CASTELLATION: CastellationPage(ui),
            Step.SNAP: SnapPage(ui),
            Step.BOUNDARY_LAYER: None,
            Step.REFINEMENT: None,
        }

        self._connectSignalsSlots()

    def load(self):
        step = app.db.getEnumValue('step')

        for s in range(step):
            if self._pages[s].isNextStepAvailable():
                self._navigation.enableStep(s)
            else:
                step = s
                break

        self._open(step)

    def isOpenedStep(self, step):
        return step == self._openedStep

    def openNextStep(self):
        step = self._navigation.currentStep() + 1
        self._open(step)
        self._navigation.setCurrentStep(self._openedStep)

    def _connectSignalsSlots(self):
        self._navigation.currentStepChanged.connect(self._moveToStep)
        self._buttons.nextButton.clicked.connect(self.openNextStep)
        self._buttons.unlockButton.clicked.connect(self._unlockCurrentStep)

    def _open(self, step):
        self._pages[step].clearResult()
        self._pages[step].unlock()
        self._pages[step].open()

        self._navigation.enableStep(step)
        self._openedStep = step

        self._navigation.setCurrentStep(self._openedStep)

        db = app.db.checkout()
        db.setValue('step', step)
        app.db.commit(db)

    def _moveToStep(self, step, prev):
        self._pages[prev].deselected()

        page = self._pages[step]
        page.selected()
        self._contentStack.setCurrentIndex(step)

        if self.isOpenedStep(step):
            self._buttons.setToOpenedMode()
            self._buttons.setNextEnabled(page.isNextStepAvailable())
        else:
            page.lock()
            self._buttons.setToLockedMode()

    def _unlockCurrentStep(self):
        currentStep = self._navigation.currentStep()
        self._resetSteps(currentStep)

        app.window.meshManager.clear()

        self._pages[currentStep].unlock()

        self._buttons.nextButton.setEnabled(True)
        self._buttons.setToOpenedMode()

    def _resetSteps(self, baseStep):
        for step in range(baseStep + 1, self._openedStep + 1):
            self._navigation.disableStep(step)
            self._pages[step].clearResult()
