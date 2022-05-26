#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QListWidgetItem

from coredb import coredb
from .models_page_ui import Ui_ModelsPage
from .multiphase_dialog import MultiphaseModelDialog
from .turbulence_dialog import TurbulenceModelDialog
from .radiation_dialog import RadiationDialog


class ListIndex(Enum):
    MULTIPHASE_MODEL = QListWidgetItem.ItemType.UserType
    TURBULANCE = auto()
    RADIATION = auto()
    SPECIES = auto()


class ModelsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ModelsPage()
        self._ui.setupUi(self)

        self._dialog = None

        self._db = coredb.CoreDB()

        self._connectSignalsSlots()

        self._addModel(self.tr("Multiphase"), "Off", ListIndex.MULTIPHASE_MODEL)
        self._addModel(self.tr("Turbulence"), "Laminar", ListIndex.TURBULANCE)
        self._addModel(self.tr("Radiation"), "Off", ListIndex.RADIATION)
        self._addModel(self.tr("Species"), "Off", ListIndex.SPECIES)

    def hideEvent(self, ev):
        if ev.spontaneous():
            return

    def showEvent(self, ev):
        if ev.spontaneous():
            return

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._modelSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _modelSelected(self):
        self._ui.edit.setEnabled(True)

    def _edit(self):
        type_ = self._ui.list.currentItem().type()

        if type_ == ListIndex.MULTIPHASE_MODEL.value:
            self._dialog = MultiphaseModelDialog()
            self._dialog._ui.off.setChecked(True)
            self._dialog.open()
        elif type_ == ListIndex.TURBULANCE.value:
            self._dialog = TurbulenceModelDialog()
            self._dialog.open()
        elif type_ == ListIndex.RADIATION.value:
            self._dialog = RadiationDialog()
            self._dialog._ui.off.setChecked(True)
            self._dialog.open()
        elif type_ == ListIndex.SPECIES.value:
            pass

    def _addModel(self, text, data, index):
        QListWidgetItem(text + "/" + data, self._ui.list, index.value)
