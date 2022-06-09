#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QListWidgetItem

from coredb import coredb
from .models_page_ui import Ui_ModelsPage
from .multiphase_dialog import MultiphaseModelDialog
from .turbulence_dialog import TurbulenceModelDialog
# from .radiation_dialog import RadiationDialog
from .models_db import ModelsDB


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

        self._db = coredb.CoreDB()
        self._multiphaseDialog = None
        self._turbulenceDialog = None
        # self._radiationDialog = None

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._modelSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _load(self):
        model = ModelsDB.getMultiphaseModel(self._db.getValue(ModelsDB.MULTIPHASE_MODELS_PATH + '/model'))
        self._addModel(self.tr("Multiphase"), ModelsDB.getMuliphaseModelText(model), Model.MULTIPHASE)

        model = ModelsDB.getTurbulenceModel(self._db.getValue(ModelsDB.TURBULENCE_MODELS_PATH + '/model'))
        self._addModel(self.tr("Turbulence"), ModelsDB.getTurbulenceModelText(model), Model.TURBULENCE)

    def _modelSelected(self):
        self._ui.edit.setEnabled(True)

    def _edit(self):
        model = self._ui.list.currentItem().type()

        if model == Model.MULTIPHASE.value:
            if self._multiphaseDialog is None:
                self._multiphaseDialog = MultiphaseModelDialog()
            self._multiphaseDialog.open()
        elif model == Model.TURBULENCE.value:
            if self._turbulenceDialog is None:
                self._turbulenceDialog = TurbulenceModelDialog()
            self._turbulenceDialog.open()
        # elif model == Model.RADIATION.value:
        #     if self._radiationDialog is None:
        #         self._radiationDialog = RadiationDialog()
        #     self._radiationDialog.open()
        elif model == Model.SPECIES.value:
            pass

    def _addModel(self, name, value, type_):
        QListWidgetItem(name + "/" + value, self._ui.list, type_.value)
