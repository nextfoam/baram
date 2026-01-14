#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import Models, DPMParticleType
from baramFlow.case_manager import CaseManager
from baramFlow.coredb.models_db import ModelsDB, MultiphaseModel
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.general_db import GeneralDB, SolverType
from baramFlow.coredb.project import Project
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.view.widgets.content_page import ContentPage
from .DPM.DPM_dialog import DPMDialog
from .energy_dialog import EnergyDialog
from .models_page_ui import Ui_ModelsPage
from .species_dialog import SpeciesDialog
from .turbulence_dialog import TurbulenceModelDialog
from .user_defined_scalars_dialog import UserDefinedScalarsDialog


class ModelItem(QListWidgetItem):
    def __init__(self, parent, model: Models, title, loadFunction, dialogClass = None):
        super().__init__(parent)
        self._model: Models = model
        self._title = title + ' / '
        self._load = loadFunction
        self._dialogClass = dialogClass

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

        if self.isEditable():
            self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEnabled)
        else:
            self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEnabled)

    @property
    def model(self) -> Models:
        return self._model

    @property
    def dialogClass(self):
        return self._dialogClass

    @dialogClass.setter
    def dialogClass(self, dc):
        self._dialogClass = dc


class ModelsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ModelsPage()
        self._ui.setupUi(self)

        self._dialog = None

        self._items = {}

        multiphaseModelTexts = {
            MultiphaseModel.OFF: self.tr('Off'),
            MultiphaseModel.VOLUME_OF_FLUID: self.tr('Volume of Fluid'),
        }

        turbulenceModelTexts = {
            TurbulenceModel.INVISCID: self.tr('Inviscid'),
            TurbulenceModel.LAMINAR: self.tr('Laminar'),
            TurbulenceModel.SPALART_ALLMARAS: self.tr('Spalart-Allmaras'),
            TurbulenceModel.K_EPSILON: self.tr('k-epsilon'),
            TurbulenceModel.K_OMEGA: self.tr('k-omega'),
            TurbulenceModel.DES: self.tr('DES'),
            TurbulenceModel.LES: self.tr('LES'),
        }

        solverTypeTexts = {
            SolverType.PRESSURE_BASED: self.tr('Pressure-based'),
            SolverType.DENSITY_BASED: self.tr('Density-based'),
        }

        DPMParticleTypeTexts = {
            DPMParticleType.NONE        : self.tr('None'),
            DPMParticleType.INERT       : self.tr('Inert'),
            DPMParticleType.DROPLET     : self.tr('Droplet'),
            DPMParticleType.COMBUSTING  : self.tr('Combusting')
        }

        self._addModelItem(Models.TURBULENCE,
                           self.tr('Turbulence'),
                           lambda: turbulenceModelTexts[TurbulenceModelsDB.getModel()], TurbulenceModelDialog)

        self._addModelItem(Models.ENERGY,
                           self.tr('Energy'),
                           lambda: self.tr('Include') if ModelsDB.isEnergyModelOn() else self.tr('Not Include'),
                           EnergyDialog)

        self._addModelItem(Models.MULTIPHASE,
                           self.tr('Multiphase'),
                           lambda: multiphaseModelTexts[ModelsDB.getMultiphaseModel()])

        self._addModelItem(Models.SOLVER_TYPE,
                           self.tr('Solver Type'),
                           lambda: solverTypeTexts[GeneralDB.getSolverType()])

        self._addModelItem(Models.SPECIES,
                           self.tr('Species'),
                           lambda: self.tr('Include') if ModelsDB.isSpeciesModelOn() else self.tr('Not Include'),
                           None if ModelsDB.isMultiphaseModelOn() or GeneralDB.isDensityBased() else SpeciesDialog)

        self._addModelItem(Models.SCALARS,
                           self.tr('User-defined Scalars'),
                           lambda: self.tr('Defined') if UserDefinedScalarsDB.hasDefined() else self.tr('Not Defined'),
                           UserDefinedScalarsDialog if GeneralDB.isPressureBased() else None)

        for i in range(self._ui.list.count()):
            self._ui.list.item(i).load()

        self._connectSignalsSlots()
        self._updateEnabled()

    def _connectSignalsSlots(self):
        Project.instance().solverStatusChanged.connect(self._updateEnabled)
        # app.meshUpdated.connect(self._meshUpdated)

        self._ui.list.itemSelectionChanged.connect(self._selectionChanged)
        self._ui.list.itemDoubleClicked.connect(self._edit)

        self._ui.edit.clicked.connect(self._edit)

    def _updateEnabled(self):
        caseManager = CaseManager()
        if caseManager.isActive():
            self._ui.list.setEnabled(False)
            self._ui.edit.setEnabled(False)
        else:
            self._ui.list.setEnabled(True)
            self._selectionChanged()

    def _selectionChanged(self):
        if self._ui.list.selectedItems():
            self._ui.edit.setEnabled(True)
        else:
            self._ui.edit.setEnabled(False)

    def _edit(self):
        if CaseManager().isActive():
            return

        self._dialog = self._ui.list.currentItem().openDialog(self)

    def _addModelItem(self, model, title, loadFunction, dialogClass=None):
        self._ui.list.addItem(ModelItem(self._ui.list, model, title, loadFunction, dialogClass))
