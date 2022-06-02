#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.widgets.resizable_dialog import ResizableDialog
from .interface_dialog_ui import Ui_InterfaceDialog
from .boundary_radio_group import BoundaryRadioGroup


class Mode(Enum):
    INTERNAL_INTERFACE = 0
    ROTATIONAL_PERIODIC = auto()
    TRANSLATIONAL_PERIODIC = auto()
    REGION_INTERFACE = auto()


class InterfaceDialog(ResizableDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_InterfaceDialog()
        self._ui.setupUi(self)

        self._boundaryRadios = BoundaryRadioGroup()
        self._boundaryRadios.setup(self._ui.boundaryList, "cyclicAMI")

        self._connectSignalsSlots()

        self._modeChanged(0)

    def _connectSignalsSlots(self):
        self._ui.mode.currentIndexChanged.connect(self._modeChanged)

    def _modeChanged(self, index):
        self._ui.rotationalPeriodic.setVisible(index == Mode.ROTATIONAL_PERIODIC.value)
        self._ui.translationalPeriodic.setVisible(index == Mode.TRANSLATIONAL_PERIODIC.value)
