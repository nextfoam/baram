#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QListWidgetItem

from coredb.models_db import ModelsDB
from .models_page_ui import Ui_ModelsPage
from .turbulence_dialog import TurbulenceModelDialog
from .energy_dialog import EnergyDialog
# from .radiation_dialog import RadiationDialog


class Model(Enum):
    TURBULENCE = QListWidgetItem.ItemType.UserType
    ENERGY = auto()
    RADIATION = auto()
    SPECIES = auto()


class ModelsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ModelsPage()
        self._ui.setupUi(self)

        self._dialog = None

        self._turbulenceModelItem = QListWidgetItem(self._ui.list, Model.TURBULENCE.value)
        self._energyModelItem = QListWidgetItem(self._ui.list, Model.ENERGY.value)

        self._connectSignalsSlots()

        self._load()

    def save(self):
        return True

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._modelSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _load(self):
        self._loadTurbulenceModel()
        self._loadEnergyModel()

    def _loadMultiphaseModel(self):
        self._multiphaseModelItem.setText(self.tr("Multiphase") + "/" + ModelsDB.getMultiphaseModelText())

    def _loadTurbulenceModel(self):
        self._turbulenceModelItem.setText(self.tr("Turbulence") + "/" + ModelsDB.getTurbulenceModelText())

    def _loadEnergyModel(self):
        self._energyModelItem.setText(self.tr("Energy") + "/" + ModelsDB.getEnergyModelText())

    def _modelSelected(self):
        self._ui.edit.setEnabled(True)

    def _edit(self):
        model = self._ui.list.currentItem().type()

        if model == Model.TURBULENCE.value:
            self._dialog = TurbulenceModelDialog(self)
            self._dialog.accepted.connect(self._loadTurbulenceModel)
            self._dialog.open()
        elif model == Model.ENERGY.value:
            self._dialog = EnergyDialog(self)
            self._dialog.accepted.connect(self._loadEnergyModel())
            self._dialog.open()
        # elif model == Model.RADIATION.value:
        #     if self._radiationDialog is None:
        #         self._radiationDialog = RadiationDialog()
        #     self._radiationDialog.open()
        elif model == Model.SPECIES.value:
            pass
