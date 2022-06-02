#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.widgets.resizable_dialog import ResizableDialog

from .multiphase_dialog_ui import Ui_MultiphaseDialog


class Model(Enum):
    OFF = auto()
    VOLUME_OF_FLUID = auto()
    MIXTURE = auto()


class MultiphaseModelDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MultiphaseDialog()
        self._ui.setupUi(self)

        self._ui.volumeOfFluid.hide()
        self._ui.mixture.hide()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        pass
