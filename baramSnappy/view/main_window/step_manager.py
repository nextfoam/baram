#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal

from baramSnappy.app import app
from baramSnappy.db.configurations_schema import Step
from baramSnappy.libbaram.utils import rmtree
from baramSnappy.view.step_page import StepPage
from baramSnappy.view.geometry.geometry_page import GeometryPage
from baramSnappy.view.base_grid.base_grid_page import BaseGridPage
from vbaramSnappy.view.castellation.castellation_page import CastellationPage
from vbaramSnappy.view.snap.snap_page import SnapPage
from vbaramSnappy.view.boundaryLayer.boundary_layer_page import BoundaryLayerPage
from vbaramSnappy.view.export.export_page import ExportPage
from vbaramSnappy.view.region.region_page import RegionPage


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


class StepManager(QObject):
    openedStepChanged = Signal(Step, Step)

    def __init__(self, navigation, ui):
        super().__init__()

        self._navigation = navigation
        self._openedStep = None
        self._contentStack = ui.content
        self._buttons = StepControlButtons(ui)
        self._contentPages = {}

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
        savedStep = app.db.getEnumValue('step')

        step = Step.GEOMETRY
        while step < savedStep and self._pages[step].isNextStepAvailable():
            self._navigation.enableStep(step)
            step += 1

        for s in range(step + 1, Step.LAST_STEP + 1):
            self._navigation.disableStep(s)
            self._pages[s].clearResult()

        for t in app.fileSystem.times():
            if float(t) > self._pages[Step.LAST_STEP].OUTPUT_TIME:
                path = app.fileSystem.timePath(t)
                if path.exists():
                    rmtree(path)

                for path in app.fileSystem.caseRoot().glob(f'processor*/{t}'):
                    rmtree(path)

        self._open(step)

    def saveCurrentPage(self):
        return self._pages[self._navigation.currentStep()].save()

    def isOpenedStep(self, step):
        return step == self._openedStep

    def openNextStep(self):
        self._open(self._navigation.currentStep() + 1)

    def _connectSignalsSlots(self):
        self._navigation.currentStepChanged.connect(self._moveToStep)
        self._buttons.nextButton.clicked.connect(self.openNextStep)
        self._buttons.unlockButton.clicked.connect(self._unlockCurrentStep)

    def _setOpendedStep(self, step):
        prev = self._openedStep

        self._pages[step].unlock()
        self._navigation.enableStep(step)
        self._openedStep = step

        db = app.db.checkout()
        db.setValue('step', step)
        app.db.commit(db)

        self.openedStepChanged.emit(step, prev)

    def _open(self, step):
        self._pages[step].open()
        self._setOpendedStep(step)
        self._navigation.setCurrentStep(self._openedStep)

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

        for step in range(currentStep + 1, self._openedStep + 1):
            self._navigation.disableStep(step)
            self._pages[step].clearResult()

        self._setOpendedStep(currentStep)

        self._buttons.nextButton.setEnabled(True)
        self._buttons.setToOpenedMode()
