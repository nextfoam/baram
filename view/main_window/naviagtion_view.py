#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum, auto

from PySide6.QtCore import QObject, Signal


class Step(Enum):
    NONE = -1
    GEOMETRY = auto()
    BASE_GRID = auto()
    CASTELLATION = auto()
    SNAP = auto()
    BOUNDARY_LAYER = auto()
    REFINEMENT = auto()


class NavigationView(QObject):
    stepSelected = Signal(Step)

    def __init__(self, view):
        super().__init__()
        self._view = view

        self._connectSignalsSlots()

    def setCurrentStep(self, step):
        self._view.setCurrentItem(self._view.topLevelItem(step.value))

    def _connectSignalsSlots(self):
        self._view.itemSelectionChanged.connect(self._stepSelected)

    def _stepSelected(self):
        self.stepSelected.emit(Step(self._view.indexOfTopLevelItem(self._view.currentItem())))


