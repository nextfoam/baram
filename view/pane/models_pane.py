#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .list_pane import ListPane
from view.dialog.setup.models.multiphase_model_dialog import MultiphaseModelDialog
from view.dialog.setup.models.viscous_model_dialog import ViscousModelDialog


class ModelsPane(ListPane):
    _MULTIPHASE_MODEL_INDEX = 0
    _VISCOUS_INDEX = 1
    _RADIATION_INDEX = 2
    _SPECIES_INDEX = 3

    def __init__(self):
        super().__init__()

    def load(self):
        self._ui.setTitle("Models")
        self._ui.addText("Multiphane / Off")
        self._ui.addText("Viscous / Off")
        self._ui.addText("Radiation / Off")
        self._ui.addText("Species / Off")

    def save(self):
        pass

    def edit(self):
        row = self._ui.currentRow()

        if row == self._MULTIPHASE_MODEL_INDEX:
            dialog = MultiphaseModelDialog()
            dialog._ui.off.setChecked(True)
            dialog.exec()
        elif row == self._VISCOUS_INDEX:
            dialog = ViscousModelDialog()
            dialog._ui.laminar.setChecked(True)
            dialog.exec()
        elif row == self._RADIATION_INDEX:
            pass
        elif row == self._SPECIES_INDEX:
            pass
