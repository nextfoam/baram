#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.widgets.resizable_dialog import ResizableDialog
from .interface_dialog_ui import Ui_InterfaceDialog
from .boundary_radio_group import BoundaryRadioGroup


class InterfaceDialog(ResizableDialog):
    class MODE(Enum):
        INTERNAL_INTERFACE = 0
        ROTATIONAL_PERIDDIC = auto()
        TRANSLATIONAL_PERIODIC = auto()
        REGION_INTERFACE = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_InterfaceDialog()
        self._ui.setupUi(self)

        self._boundaryRadios = BoundaryRadioGroup()

        self._setup()
        self._connectSignalsSlots()

        self._modeChanged(0)

    def _setup(self):
        self._boundaryRadios.setup(self._ui.boundaryList, "cyclicAMI")

    def _connectSignalsSlots(self):
        self._ui.mode.currentIndexChanged.connect(self._modeChanged)

    def _modeChanged(self, index):
        self._ui.rotationalPeriodic.setVisible(index == self.MODE.ROTATIONAL_PERIDDIC.value)
        self._ui.translationalPeriodic.setVisible(index == self.MODE.TRANSLATIONAL_PERIODIC.value)
        self._resizeDialog(self._ui.dialogContents)
