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


class CaseWizard(QWizard):
    class Page(IntEnum):
        LAST             = -1
        WORKSPACE        = auto()
        FLOW_TYPE        = auto()
        SOLVER_TYPE      = auto()
        ENERGY_MODEL     = auto()
        MULTIPHASE_MODEL = auto()
        GRAVITY_MODEL    = auto()
        SPECIES_MODEL    = auto()

    def __init__(self, *args, **kwargs):
        super(CaseWizard, self).__init__(*args, **kwargs)

        self._ui = Ui_CaseWizard()
        self._ui.setupUi(self)

        self.setPage(self.Page.WORKSPACE.value, WorkspacePage(self))
        self.setPage(self.Page.FLOW_TYPE.value, FlowTypePage(self))
        self.setPage(self.Page.SOLVER_TYPE.value, SolverTypePage(self))
        self.setPage(self.Page.ENERGY_MODEL.value, EnergyModelPage(self))
        self.setPage(self.Page.MULTIPHASE_MODEL.value, MultiphaseModelPage(self))
        self.setPage(self.Page.GRAVITY_MODEL.value, GravityModelPage(self))
        self.setPage(self.Page.SPECIES_MODEL.value, SpeciesModelPage(self))
        self.setStartId(self.Page.WORKSPACE.value)

    def nextId(self):
        curId = self.currentId()
        if curId == self.Page.WORKSPACE.value:
            return self.Page.FLOW_TYPE.value
        elif curId == self.Page.FLOW_TYPE.value:
            if self.field('flowTypeCompressible'):
                return self.Page.SOLVER_TYPE.value
            else:
                return self.Page.ENERGY_MODEL.value
        elif curId == self.Page.SOLVER_TYPE.value:
            return self.Page.SPECIES_MODEL.value
        elif curId == self.Page.ENERGY_MODEL.value:
            if self.field('energyModelsInclude'):
                return self.Page.GRAVITY_MODEL.value
            else:
                return self.Page.MULTIPHASE_MODEL.value
        elif curId == self.Page.MULTIPHASE_MODEL.value:
            if self.field('multiphaseModelsInclude'):
                return self.Page.GRAVITY_MODEL.value
            else:
                return self.Page.SPECIES_MODEL.value
        elif curId == self.Page.GRAVITY_MODEL.value:
            return self.Page.SPECIES_MODEL.value
        elif curId == self.Page.SPECIES_MODEL.value:
            return self.Page.LAST.value
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
