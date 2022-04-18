#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QListWidgetItem

from view.setup.models.models_page_ui import Ui_ModelsPage
from .multiphase_model_dialog import MultiphaseModelDialog
from .viscous_model_dialog import ViscousModelDialog
from .radiation_model_dialog import RadiationModelDialog


class ModelsPage(QWidget):
    class LIST_INDEX(Enum):
        MULTIPHASE_MODEL = 1000
        VISCOSE = auto()
        RADIATION = auto()
        SPECIES = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_ModelsPage()
        self._ui.setupUi(self)

        self.connectSignalsSlots()

    def connectSignalsSlots(self):
        self._ui.list.itemDoubleClicked.connect(self.edit)
        self._ui.edit.clicked.connect(self.edit)

    def load(self):
        self._addModel(self.tr("Multiphase"), self._getMultiphase(), self.LIST_INDEX.MULTIPHASE_MODEL)
        self._addModel(self.tr("Viscous"), self._getViscous(), self.LIST_INDEX.VISCOSE)
        self._addModel(self.tr("Radiation"), self._getRadiation(), self.LIST_INDEX.RADIATION)
        self._addModel(self.tr("Species"), self._getSpecies(), self.LIST_INDEX.SPECIES)

    def save(self):
        pass

    def edit(self):
        type = self._ui.list.currentItem().type()

        if type == self.LIST_INDEX.MULTIPHASE_MODEL.value:
            dialog = MultiphaseModelDialog()
            dialog._ui.off.setChecked(True)
            dialog.exec()
        elif type == self.LIST_INDEX.VISCOSE.value:
            dialog = ViscousModelDialog()
            dialog._ui.laminar.setChecked(True)
            dialog.exec()
        elif type == self.LIST_INDEX.RADIATION.value:
            dialog = RadiationModelDialog()
            dialog._ui.off.setChecked(True)
            dialog.exec()
        elif type == self.LIST_INDEX.SPECIES.value:
            pass

    def _addModel(self, text, data, index):
        modelItem = QListWidgetItem(text + "/" + data, self._ui.list, index.value)

    def _getMultiphase(self):
        return "Off"

    def _getViscous(self):
        return "Off"

    def _getRadiation(self):
        return "Off"

    def _getSpecies(self):
        return "Off"
