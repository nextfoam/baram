#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum

from PySide6.QtWidgets import QWizard

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
        FLOW_TYPE        =  0
        SOLVER_TYPE      =  1
        ENERGY_MODEL     =  2
        MULTIPHASE_MODEL =  3
        GRAVITY_MODEL    =  4
        SPECIES_MODEL    =  5

    def __init__(self, *args, **kwargs):
        super(CaseWizard, self).__init__(*args, **kwargs)

        self._ui = Ui_CaseWizard()
        self._ui.setupUi(self)

        self.setPage(self.Page.FLOW_TYPE, FlowTypePage(self))
        self.setPage(self.Page.SOLVER_TYPE, SolverTypePage(self))
        self.setPage(self.Page.ENERGY_MODEL, EnergyModelPage(self))
        self.setPage(self.Page.MULTIPHASE_MODEL, MultiphaseModelPage(self))
        self.setPage(self.Page.GRAVITY_MODEL, GravityModelPage(self))
        self.setPage(self.Page.SPECIES_MODEL, SpeciesModelPage(self))

        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.IgnoreSubTitles, True)
        self.setOption(QWizard.CancelButtonOnLeft, True)

        self.setWizardStyle(QWizard.ModernStyle)

        self.setStartId(self.Page.FLOW_TYPE)

    def nextId(self):
        if self.currentId() == self.Page.FLOW_TYPE:
            if self.field("compressibleFlow"):
                return self.Page.SOLVER_TYPE
            else:
                return self.Page.ENERGY_MODEL
        elif self.currentId() == self.Page.SOLVER_TYPE:
            return self.Page.SPECIES_MODEL
        elif self.currentId() == self.Page.ENERGY_MODEL:
            if self.field("energyModelIncluded"):
                return self.Page.SPECIES_MODEL
            else:
                return self.Page.MULTIPHASE_MODEL
        elif self.currentId() == self.Page.MULTIPHASE_MODEL:
            return self.Page.SPECIES_MODEL
        elif self.currentId() == self.Page.SPECIES_MODEL:
            return self.Page.GRAVITY_MODEL
        elif self.currentId() == self.Page.GRAVITY_MODEL:
            return self.Page.LAST
        else:
            raise NotImplementedError('Unknown Case Wizard Page')

