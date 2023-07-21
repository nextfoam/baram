#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import QObject, Signal

from db.configurations_schema import Step
from view.geometry.geometry_page import GeometryPage
from view.base_grid.base_grid_page import BaseGridPage
from view.castellation.castellation_page import CastellationPage

STEP_CLASSES = {
    Step.GEOMETRY.value: GeometryPage,
    # Step.REGION.value: RegionPage,
    Step.BASE_GRID.value: BaseGridPage,
    Step.CASTELLATION.value: CastellationPage,
    Step.SNAP.value: None,
    Step.BOUNDARY_LAYER.value: None,
    Step.REFINEMENT.value: None,
}


def isStepCompleted(step):
    return STEP_CLASSES[step].nextStepAvailable()


class ContentView(QObject):
    nextStepAvailableChanged = Signal(bool)

    def __init__(self, ui):
        super().__init__()
        self._view = ui.content
        self._page = None

        self._view.setLayout(QVBoxLayout())
        self._view.layout().setContentsMargins(0, 0, 0, 0)

    def moveToStep(self, step, opened):
        if item := self._view.layout().takeAt(0):
            item.widget().close()
            item.widget().deleteLater()

        if creator := STEP_CLASSES[step]:
            self._page = creator()
            self._page.nextStepAvailableChanged.connect(self.nextStepAvailableChanged)
            if not opened:
                self._page.lock()
            self._view.layout().addWidget(self._page)

    def unlock(self):
        self._page.unlock()

    def open(self):
        self._page.clearResult()

    def nextStepAvailable(self):
        return self._page.nextStepAvailable()

    def _nextStepAvailableChanged(self):
        self.nextStepAvailableChanged.emit(self._page.nextStepAvailable())
