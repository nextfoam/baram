#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtGui import QBrush, QColor

from baram.coredb.models_db import ModelsDB, MultiphaseModel, TurbulenceModel
from baram.coredb.general_db import GeneralDB, SolverType
from baram.view.widgets.content_page import ContentPage
from .models_page_ui import Ui_ModelsPage
from .turbulence_dialog import TurbulenceModelDialog
from .energy_dialog import EnergyDialog
# from .radiation_dialog import RadiationDialog


grayBrush = QBrush(QColor('#5c5c5c'))


class ModelItem(QListWidgetItem):

    def __init__(self, parent, title, loadFunction, dialogClass=None):
        super().__init__(parent)
        self._title = title + ' / '
        self._load = loadFunction
        self._dialogClass = dialogClass

        if not self.isEditable():
            self.setFlags(~Qt.ItemIsSelectable)
            self.setForeground(grayBrush)

    def isEditable(self):
        return self._dialogClass is not None

    def openDialog(self, parent):
        if self._dialogClass:
            dialog = self._dialogClass(parent)
            dialog.accepted.connect(self.load)
            dialog.open()
            return dialog

        return None

    def load(self):
        self.setText(self._title + self._load())


class ModelsPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ModelsPage()
        self._ui.setupUi(self)

        self._dialog = None

        self._items = {}

        multiphaseModelText = {
            MultiphaseModel.OFF: self.tr('Off'),
            MultiphaseModel.VOLUME_OF_FLUID: self.tr('Volume of Fluid'),
        }

        turbulenceModelText = {
            TurbulenceModel.INVISCID: self.tr('Inviscid'),
            TurbulenceModel.LAMINAR: self.tr('Laminar'),
            TurbulenceModel.SPALART_ALLMARAS: self.tr('Spalart-Allmaras'),
            TurbulenceModel.K_EPSILON: self.tr('k-epsilon'),
            TurbulenceModel.K_OMEGA: self.tr('k-omega'),
            TurbulenceModel.LES: self.tr('LES'),
        }

        solverTypeText = {
            SolverType.PRESSURE_BASED: self.tr('Pressure-based'),
            SolverType.DENSITY_BASED: self.tr('Density-based'),
        }

        self._addModelItem(
            self.tr('Turbulence'), lambda: turbulenceModelText[ModelsDB.getTurbulenceModel()], TurbulenceModelDialog)
        self._addModelItem(
            self.tr('Energy'),
            lambda: self.tr('Include') if ModelsDB.isEnergyModelOn() else self.tr('Not Include'), EnergyDialog)

        self._addModelItem(
            self.tr('Flow Type'),
            lambda: self.tr('Compressible') if GeneralDB.isCompressible() else self.tr('Incompressible'))
        self._addModelItem(self.tr('Multiphase'), lambda: multiphaseModelText[ModelsDB.getMultiphaseModel()])
        self._addModelItem(self.tr('Solver Type'), lambda: solverTypeText[GeneralDB.getSolverType()])
        self._addModelItem(
            self.tr('Species'),
            lambda: self.tr('Include') if ModelsDB.isSpeciesModelOn() else self.tr('Not Include'))

        self._connectSignalsSlots()

        for i in range(self._ui.list.count()):
            self._ui.list.item(i).load()

    def _connectSignalsSlots(self):
        self._ui.list.currentItemChanged.connect(self._modelSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)

    def _modelSelected(self, item):
        self._ui.edit.setEnabled(item.isEditable())

    def _edit(self):
        self._dialog = self._ui.list.currentItem().openDialog(self)

    def _addModelItem(self, title, loadFunction, dialogClass=None):
        self._ui.list.addItem(ModelItem(self._ui.list, title, loadFunction, dialogClass))
