#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QListWidgetItem

from coredb.models_db import ModelsDB
from .models_page_ui import Ui_ModelsPage
from .multiphase_dialog import MultiphaseModelDialog
from .turbulence_dialog import TurbulenceModelDialog
# from .radiation_dialog import RadiationDialog


class Model(Enum):
    MULTIPHASE = QListWidgetItem.ItemType.UserType
    TURBULENCE = auto()
    RADIATION = auto()
    SPECIES = auto()


class ModelsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ModelsPage()
        self._ui.setupUi(self)

        self._multiphaseDialog = None
        self._turbulenceDialog = None
        # self._radiationDialog = None

        self._multiphaseModelItem = QListWidgetItem(self._ui.list, Model.MULTIPHASE.value)
        self._turbulenceModelItem = QListWidgetItem(self._ui.list, Model.TURBULENCE.value)

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._modelSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _load(self):
        self._loadMultiphaseModel()
        self._loadTurbulenceModel()

    def _loadMultiphaseModel(self):
        self._multiphaseModelItem.setText(self.tr("Multiphase") + "/" + ModelsDB.getMultiphaseModelText())

    def _loadTurbulenceModel(self):
        self._turbulenceModelItem.setText(self.tr("Turbulence") + "/" + ModelsDB.getTurbulenceModelText())

    def _modelSelected(self):
        self._ui.edit.setEnabled(True)

    def _edit(self):
        model = self._ui.list.currentItem().type()

        if model == Model.MULTIPHASE.value:
            if self._multiphaseDialog is None:
                self._multiphaseDialog = MultiphaseModelDialog(self)
                self._multiphaseDialog.accepted.connect(self._loadMultiphaseModel)
            self._multiphaseDialog.open()
        elif model == Model.TURBULENCE.value:
            if self._turbulenceDialog is None:
                self._turbulenceDialog = TurbulenceModelDialog(self)
                self._turbulenceDialog.accepted.connect(self._loadTurbulenceModel)
            self._turbulenceDialog.open()
        # elif model == Model.RADIATION.value:
        #     if self._radiationDialog is None:
        #         self._radiationDialog = RadiationDialog()
        #     self._radiationDialog.open()
        elif model == Model.SPECIES.value:
            pass
