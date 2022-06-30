#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum

from PySide6.QtWidgets import QWizard

from coredb import coredb

from .case_wizard_ui import Ui_CaseWizard

from .flow_type_page import FlowTypePage
from .solver_type_page import SolverTypePage
from .energy_model_page import EnergyModelPage
from .multiphase_model_page import MultiphaseModelPage
from .gravity_model_page import GravityModelPage
from .species_model_page import SpeciesModelPage


class CaseWizard(QWizard):
    class Page(IntEnum):
        LAST             = -1
        FLOW_TYPE        = 0
        SOLVER_TYPE      = 1
        ENERGY_MODEL     = 2
        MULTIPHASE_MODEL = 3
        GRAVITY_MODEL    = 4
        SPECIES_MODEL    = 5

    def __init__(self, *args, **kwargs):
        super(CaseWizard, self).__init__(*args, **kwargs)

        self._db = coredb.CoreDB()

        self._ui = Ui_CaseWizard()
        self._ui.setupUi(self)

        self.setPage(self.Page.FLOW_TYPE, FlowTypePage(self))
        self.setPage(self.Page.SOLVER_TYPE, SolverTypePage(self))
        self.setPage(self.Page.ENERGY_MODEL, EnergyModelPage(self))
        self.setPage(self.Page.MULTIPHASE_MODEL, MultiphaseModelPage(self))
        self.setPage(self.Page.GRAVITY_MODEL, GravityModelPage(self))
        self.setPage(self.Page.SPECIES_MODEL, SpeciesModelPage(self))

        self.setStartId(self.Page.FLOW_TYPE)


    def nextId(self):
        if self.currentId() == self.Page.FLOW_TYPE:
            if self.field("flowType"):
                return self.Page.SOLVER_TYPE
            else:
                return self.Page.ENERGY_MODEL
        elif self.currentId() == self.Page.SOLVER_TYPE:
            return self.Page.SPECIES_MODEL
        elif self.currentId() == self.Page.ENERGY_MODEL:
            if self.field("energyModels"):
                return self.Page.GRAVITY_MODEL
            else:
                return self.Page.MULTIPHASE_MODEL
        elif self.currentId() == self.Page.MULTIPHASE_MODEL:
            if self.field("multiphaseModels"):
                return self.Page.GRAVITY_MODEL
            else:
                return self.Page.SPECIES_MODEL
        elif self.currentId() == self.Page.GRAVITY_MODEL:
            return self.Page.SPECIES_MODEL

        elif self.currentId() == self.Page.SPECIES_MODEL:
            return self.Page.LAST
        else:
            raise NotImplementedError("Unknown Case Wizard Page")


    def accept(self):
        general_path = ".//general"
        models_path = ".//models"

        if self.field("flowType") == "True":
            self._db.setValue(f"{general_path}/flowType", "compressible")
        else:
            self._db.setValue(f"{general_path}/flowType", "incompressible")

        if self.field("solverType") == "True":
            self._db.setValue(f"{general_path}/solverType", "pressureBased")
        else:
            self._db.setValue(f"{general_path}/solverType", "densityBased")

        if self.field("energyModels") == "True":
            self._db.setValue(f"{models_path}/energyModels", "on")
        else:
            self._db.setValue(f"{models_path}/energyModels", "off")

        if self.field("multiphaseModel") == "True":
            self._db.setValue(f"{models_path}/multiphaseModels/model", "on")
        else:
            self._db.setValue(f"{models_path}/multiphaseModels/model", "off")

        if self.field("gravity") == "True":
            self._db.setAttribute(f"{general_path}/operatingConditions/gravity", "disabled", "true")
            self._db.setValue(f"{general_path}/operatingConditions/gravity/direction/x", self.field("gravity_x"))
            self._db.setValue(f"{general_path}/operatingConditions/gravity/direction/y", self.field("gravity_y"))
            self._db.setValue(f"{general_path}/operatingConditions/gravity/direction/z", self.field("gravity_z"))
        else:
            self._db.setAttribute(f"{general_path}/operatingConditions/gravity", "disabled", "false")

        if self.field("speciesModel") == "True":
            self._db.setValue(f"{models_path}/speciesModels", "on")
        else:
            self._db.setValue(f"{models_path}/speciesModels", "off")

        #
        self.close()
