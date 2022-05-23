#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .multiphase_model_dialog_ui import Ui_MultiphaseModelDialog


class MultiphaseModelDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MultiphaseModelDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        pass
