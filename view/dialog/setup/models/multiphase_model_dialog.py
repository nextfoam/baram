#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .multiphase_model_dialog_ui import Ui_MultiphaseModelDialog
from view.dialog.baram_dialog import BaramDialog


class MultiphaseModelDialog(BaramDialog):
    def __init__(self):
        super().__init__(Ui_MultiphaseModelDialog())

    def connectSignalsSlots(self):
        pass
