#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

from PySide6.QtWidgets import QWizard

from coredb import coredb
from .case_wizard_ui import Ui_CaseWizard
from .flow_type_page import FlowTypePage
from .solver_type_page import SolverTypePage
from .energy_model_page import EnergyModelPage
from .multiphase_model_page import MultiphaseModelPage
from .gravity_model_page import GravityModelPage
from .species_model_page import SpeciesModelPage
from .workspace_page import WorkspacePage

LAST = -1
WORKSPACE = 0
FLOW_TYPE = 1
SOLVER_TYPE = 2
ENERGY_MODEL = 3
MULTIPHASE_MODEL = 4
GRAVITY_MODEL = 5
SPECIES_MODEL = 6

class CaseWizard(QWizard):
    def __init__(self, *args, **kwargs):
        super(CaseWizard, self).__init__(*args, **kwargs)

        self._ui = Ui_CaseWizard()
        self._ui.setupUi(self)

        self.setPage(WORKSPACE, WorkspacePage(self))
        self.setPage(FLOW_TYPE, FlowTypePage(self))
        self.setPage(SOLVER_TYPE, SolverTypePage(self))
        self.setPage(ENERGY_MODEL, EnergyModelPage(self))
        self.setPage(MULTIPHASE_MODEL, MultiphaseModelPage(self))
        self.setPage(GRAVITY_MODEL, GravityModelPage(self))
        self.setPage(SPECIES_MODEL, SpeciesModelPage(self))
        self.setStartId(WORKSPACE)

    def nextId(self):
        curId = self.currentId()
        if curId == WORKSPACE:
            return FLOW_TYPE
        elif curId == FLOW_TYPE:
            if self.field('flowTypeCompressible'):
                return SOLVER_TYPE
            else:
                return ENERGY_MODEL
        elif curId == SOLVER_TYPE:
            return SPECIES_MODEL
        elif curId == ENERGY_MODEL:
            if self.field('energyModelsInclude'):
                return GRAVITY_MODEL
            else:
                return MULTIPHASE_MODEL
        elif curId == MULTIPHASE_MODEL:
            if self.field('multiphaseModelsInclude'):
                return GRAVITY_MODEL
            else:
                return SPECIES_MODEL
        elif curId == GRAVITY_MODEL:
            return SPECIES_MODEL
        elif curId == SPECIES_MODEL:
            return LAST
        else:
            raise NotImplementedError('Unknown Case Wizard Page')

    def accept(self):
        db = coredb.CoreDB()

        generalXPath = './/general'
        gravityXPath = './/general/operatingConditions/gravity'
        modelsXPath = './/models'

        if self.field('flowTypeCompressible'):
            db.setValue(f'{generalXPath}/flowType', 'compressible')
        else:
            db.setValue(f'{generalXPath}/flowType', 'incompressible')

        if self.field('solverTypePressureBased'):
            db.setValue(f'{generalXPath}/solverType', 'pressureBased')
        else:
            db.setValue(f'{generalXPath}/solverType', 'densityBased')

        if self.field('energyModelsInclude'):
            db.setValue(f'{modelsXPath}/energyModels', 'on')
        else:
            db.setValue(f'{modelsXPath}/energyModels', 'off')

        if self.field('multiphaseModelsInclude'):
            db.setValue(f'{modelsXPath}/multiphaseModels/model', 'on')
        else:
            db.setValue(f'{modelsXPath}/multiphaseModels/model', 'off')

        if self.field('gravityInclude'):
            db.setAttribute(f'{gravityXPath}', 'disabled', 'false')
            db.setValue(f'{gravityXPath}/direction/x', self.field('gravityX'))
            db.setValue(f'{gravityXPath}/direction/y', self.field('gravityY'))
            db.setValue(f'{gravityXPath}/direction/z', self.field('gravityZ'))
        else:
            db.setAttribute(f'{gravityXPath}', 'disabled', 'true')

        if self.field('speciesModelsInclude'):
            db.setValue(f'{modelsXPath}/speciesModels', 'on')
        else:
            db.setValue(f'{modelsXPath}/speciesModels', 'off')

        super().accept()
