#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QObject, Signal

import qasync

from baramMesh.openfoam.utility.snappy_hex_mesh import snappyHexMesh
from libbaram.utils import rmtree

from baramMesh.app import app
from baramMesh.db.configurations_schema import Step
from baramMesh.view.step_page import StepPage
from baramMesh.view.geometry.geometry_page import GeometryPage
from baramMesh.view.base_grid.base_grid_page import BaseGridPage
from baramMesh.view.castellation.castellation_page import CastellationPage
from baramMesh.view.snap.snap_page import SnapPage
from baramMesh.view.boundaryLayer.boundary_layer_page import BoundaryLayerPage
from baramMesh.view.export.export_page import ExportPage
from baramMesh.view.region.region_page import RegionPage
from widgets.async_message_box import AsyncMessageBox


class ButtonID(Enum):
    NEXT    = auto()
    FINISH  = auto()
    CANCEL  = auto()
    UNLOCK  = auto()


class StepControlButtons(QObject):
    nextButtonClicked = Signal()
    finishButtonClicked = Signal()
    cancelButtonClicked = Signal()
    unlockButtonClicked = Signal()

    def __init__(self, ui):
        super().__init__()

        self._cancelClicked = False

        self._buttons = {
            ButtonID.NEXT:      ui.next,
            ButtonID.FINISH:    ui.finishSteps,
            ButtonID.CANCEL:    ui.finishCancel,
            ButtonID.UNLOCK:    ui.unlock
        }

        ui.next.clicked.connect(self.nextButtonClicked)
        ui.finishSteps.clicked.connect(self.finishButtonClicked)
        ui.finishCancel.clicked.connect(self._onCancelButtonClicked)
        ui.unlock.clicked.connect(self.unlockButtonClicked)

    def isCancelClicked(self):
        return self._cancelClicked

    def showButton(self, id_, enabled=True):
        self._cancelClicked = False

        for i, button in self._buttons.items():
            if i == id_:
                button.show()
                button.setEnabled(enabled)
            else:
                button.hide()

    def enableNextButton(self):
        self._buttons[ButtonID.NEXT].setEnabled(True)

    def disableNextButton(self):
        self._buttons[ButtonID.NEXT].setEnabled(False)

    def _onCancelButtonClicked(self):
        self._cancelClicked = True
        self.cancelButtonClicked.emit()


class StepManager(QObject):
    displayStepChanged = Signal(Step)
    workingStepChanged = Signal(Step)

    def __init__(self, navigation, ui):
        super().__init__()

        self._navigation = navigation
        self._workingStep = Step.NONE
        self._contentStack = ui.content
        self._buttons = StepControlButtons(ui)
        self._contentPages = {}

        self._batchRunning = False

        self._pages = {
            Step.NONE: StepPage(ui, None),
            Step.GEOMETRY: GeometryPage(ui),
            Step.REGION: RegionPage(ui),
            Step.BASE_GRID: BaseGridPage(ui),
            Step.CASTELLATION: CastellationPage(ui),
            Step.SNAP: SnapPage(ui),
            Step.BOUNDARY_LAYER: BoundaryLayerPage(ui),
            Step.EXPORT: ExportPage(ui),
        }

        self._connectSignalsSlots()

    def load(self):
        for page in self._pages.values():
            page.unload()
            page.load()

        savedStep = app.db.getEnum('step')

        step = Step.GEOMETRY
        while step < savedStep and self._pages[step].isNextStepAvailable():
            self._navigation.enableStep(step)
            step += 1

        for s in range(step + 1, Step.LAST_STEP + 1):
            self._navigation.disableStep(s)
            self._pages[Step(s)].clearResult()

        for t in app.fileSystem.times():
            if float(t) > self._pages[Step.LAST_STEP].OUTPUT_TIME:
                path = app.fileSystem.timePath(t)
                if path.exists():
                    rmtree(path)

                for path in app.fileSystem.caseRoot().glob(f'processor*/{t}'):
                    rmtree(path)

        self._open(step)

    def currentPage(self):
        return self._pages[self._navigation.currentStep()]

    async def saveCurrentPage(self):
        return await self.currentPage().save()

    def openNextStep(self):
        self._open(self._workingStep + 1)

    def retranslatePages(self):
        for page in self._pages.values():
            page.retranslate()

    def _connectSignalsSlots(self):
        self._navigation.currentStepChanged.connect(self._moveToStep)
        self._buttons.nextButtonClicked.connect(self.openNextStep)
        self._buttons.finishButtonClicked.connect(self._finishSteps)
        self._buttons.cancelButtonClicked.connect(self._cancelFinishSteps)
        self._buttons.unlockButtonClicked.connect(self._unlockCurrentStep)

        for step in range(Step.GEOMETRY, Step.CASTELLATION):
            self._pages[step].stepCompleted.connect(self._buttons.enableNextButton)
            self._pages[step].stepReset.connect(self._buttons.disableNextButton)

        for step in range(Step.CASTELLATION, Step.EXPORT):
            self._pages[step].stepCompleted.connect(lambda: self._buttons.showButton(ButtonID.NEXT))
            self._pages[step].stepReset.connect(lambda: self._buttons.showButton(ButtonID.FINISH))

        self._pages[Step.GEOMETRY].geometryRemoved.connect(self._geometryRemoved)

    def _isWorkingStep(self, step):
        return step == self._workingStep

    def _setWorkingStep(self, step):
        self._pages[step].unlock()
        self._navigation.setWorkingStep(step)
        self._workingStep = step

        db = app.db.checkout()
        db.setValue('step', step)
        app.db.commit(db)

        self.workingStepChanged.emit(step)

    def _open(self, step):
        self._pages[step].open()
        self._navigation.setCurrentStep(step)
        self._setWorkingStep(step)

    @qasync.asyncSlot()
    async def _moveToStep(self, step, prev):
        if step == prev:
            return

        if not await self._pages[prev].hide():
            self._navigation.setCurrentStep(prev)
            return

        page = self._pages[step]
        await page.show(self._isWorkingStep(step), self._batchRunning)
        if step < self._workingStep or self._batchRunning or snappyHexMesh.isRunning():
            page.lock()
        else:
            page.unlock()

        self._contentStack.setCurrentIndex(step)

        self._updateControlButtons(step)
        self.displayStepChanged.emit(step)

    @qasync.asyncSlot()
    async def _finishSteps(self):
        self._batchRunning = True
        self._buttons.showButton(ButtonID.CANCEL)

        snappyHexMesh.snappyStarted.emit()

        while self._workingStep < Step.EXPORT:
            # Only change workingStep
            self._pages[self._workingStep].load()
            self._navigation.setWorkingStep(self._workingStep)

            if self._buttons.isCancelClicked() or not await self._pages[self._workingStep].runInBatchMode():
                break

            self._workingStep += 1
        else:
            await AsyncMessageBox().information(self._contentStack, self.tr('Process Completed'),
                                                self.tr('All steps complete.'))

        # Apply current workingStep
        self._setWorkingStep(self._workingStep)

        self._batchRunning = False

        displayStep = self._navigation.currentStep()
        self._updateControlButtons(displayStep)
        if displayStep < self._workingStep:
            self.currentPage().lock()

        snappyHexMesh.snappyStopped.emit()

        self.currentPage().updateWorkingStatus()

    def _cancelFinishSteps(self):
        snappyHexMesh.cancel()

    @qasync.asyncSlot()
    async def _unlockCurrentStep(self):
        currentStep = self._navigation.currentStep()

        try:
            for step in range(currentStep + 1, self._workingStep + 1):
                self._navigation.disableStep(step)
                self._pages[Step(step)].clearResult()
        except PermissionError:
            await AsyncMessageBox().information(
                self._contentStack,
                self.tr('Permission Error'),
                self.tr('Permission Error:\n'
                        'A file in the project folder might be open in another program.\n'
                        'Close the file and try again.'))

            return

        self._setWorkingStep(currentStep)

        # self._buttons.nextButton.setEnabled(True)
        # self._buttons.setToOpenedMode()
        self._updateControlButtons(currentStep)

    def _geometryRemoved(self):
        self._pages[Step.CASTELLATION].unload()
        self._pages[Step.BOUNDARY_LAYER].unload()

    def _updateControlButtons(self, step):
        if self._batchRunning:
            return

        if self._pages[step].isNextStepAvailable():
            if self._isWorkingStep(step):
                self._buttons.showButton(ButtonID.NEXT)
            else:
                self._buttons.showButton(ButtonID.UNLOCK)
        elif self._isWorkingStep(step) and step in (Step.CASTELLATION, Step.SNAP, Step.BOUNDARY_LAYER):
            self._buttons.showButton(ButtonID.FINISH)
        else:
            self._buttons.showButton(ButtonID.NEXT, False)
