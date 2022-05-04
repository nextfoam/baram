#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QListWidgetItem

from view.setup.models.models_page_ui import Ui_ModelsPage
from .multiphase_model_dialog import MultiphaseModelDialog
from .turbulence_model_dialog import TurbulenceModelDialog
from .radiation_model_dialog import RadiationModelDialog


class ModelsPage(QWidget):
    class LIST_INDEX(Enum):
        MULTIPHASE_MODEL = QListWidgetItem.ItemType.UserType
        TURBULANCE = auto()
        RADIATION = auto()
        SPECIES = auto()

    def __init__(self):
        super().__init__()
        self._ui = Ui_ModelsPage()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _edit(self):
        type = self._ui.list.currentItem().type()

        if type == self.LIST_INDEX.MULTIPHASE_MODEL.value:
            dialog = MultiphaseModelDialog()
            dialog._ui.off.setChecked(True)
            dialog.exec()
        elif type == self.LIST_INDEX.TURBULANCE.value:
            dialog = TurbulenceModelDialog()
            dialog._ui.laminar.setChecked(True)
            dialog.exec()
        elif type == self.LIST_INDEX.RADIATION.value:
            dialog = RadiationModelDialog()
            dialog._ui.off.setChecked(True)
            dialog.exec()
        elif type == self.LIST_INDEX.SPECIES.value:
            pass

    def _addModel(self, text, data, index):
        QListWidgetItem(text + "/" + data, self._ui.list, index.value)

    def load(self):
        self._addModel(self.tr("Multiphase"), "Off", self.LIST_INDEX.MULTIPHASE_MODEL)
        self._addModel(self.tr("Turbulence"), "Laminar", self.LIST_INDEX.TURBULANCE)
        self._addModel(self.tr("Radiation"), "Off", self.LIST_INDEX.RADIATION)
        self._addModel(self.tr("Species"), "Off", self.LIST_INDEX.SPECIES)

    def save(self):
        pass
