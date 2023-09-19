#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizard

from baram.coredb import coredb
from baram.coredb.models_db import MultiphaseModel
from .case_wizard_ui import Ui_CaseWizard
from .flow_type_page import FlowTypePage
from .solver_type_page import SolverTypePage
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

        self._db = coredb.createDB()

        self._ui = Ui_CaseWizard()
        self._ui.setupUi(self)

        self.setPage(WORKSPACE, WorkspacePage(self))
        self.setPage(FLOW_TYPE, FlowTypePage(self))
        self.setPage(SOLVER_TYPE, SolverTypePage(self))
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
                return MULTIPHASE_MODEL
        elif curId == SOLVER_TYPE:
            return SPECIES_MODEL
        elif curId == MULTIPHASE_MODEL:
            if self.field('multiphaseModel') == MultiphaseModel.OFF.value:
                return SPECIES_MODEL
            else:
                return GRAVITY_MODEL
        elif curId == GRAVITY_MODEL:
            return SPECIES_MODEL
        elif curId == SPECIES_MODEL:
            return LAST
        else:
            raise NotImplementedError('Unknown Case Wizard Page')

    def accept(self):
        generalXPath = './/general'
        gravityXPath = './/general/operatingConditions/gravity'
        modelsXPath = './/models'

        if self.field('flowTypeCompressible'):
            self._db.setValue(f'{generalXPath}/flowType', 'compressible')
            self._db.setValue(f'{modelsXPath}/energyModels', 'on')
        else:
            self._db.setValue(f'{generalXPath}/flowType', 'incompressible')
            self._db.setValue(f'{modelsXPath}/energyModels', 'off')

        if self.field('solverTypePressureBased'):
            self._db.setValue(f'{generalXPath}/solverType', 'pressureBased')
        else:
            self._db.setValue(f'{generalXPath}/solverType', 'densityBased')

        self._db.setValue(f'{modelsXPath}/multiphaseModels/model', self.field('multiphaseModel'))

        if self.field('multiphaseModel') != MultiphaseModel.OFF.value:
            self._db.setValue(f'{gravityXPath}/direction/x', self.field('gravityX'))
            self._db.setValue(f'{gravityXPath}/direction/y', self.field('gravityY'))
            self._db.setValue(f'{gravityXPath}/direction/z', self.field('gravityZ'))

        if self.field('speciesModelsInclude'):
            self._db.setValue(f'{modelsXPath}/speciesModels', 'on')
        else:
            self._db.setValue(f'{modelsXPath}/speciesModels', 'off')

        super().accept()

    def reject(self):
        coredb.destroy()

        super().reject()
