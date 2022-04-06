#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.dialog.baram_dialog import BaramDialog
from .multiphase_model_dialog_ui import Ui_MultiphaseModelDialog


class MultiphaseModelDialog(BaramDialog):
    def __init__(self):
        super().__init__(Ui_MultiphaseModelDialog())

    def connectSignalsSlots(self):
        pass
