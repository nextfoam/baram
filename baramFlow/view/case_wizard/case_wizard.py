#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QWizard

from baramFlow.base.material.material import DensitySpecification
from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import MultiphaseModel
from baramFlow.coredb.numerical_db import NumericalDB
from .case_wizard_ui import Ui_CaseWizard
from .flow_type_page import FlowTypePage
from .gravity_model_page import GravityModelPage
from .last_page import LastPage
from .multiphase_model_page import MultiphaseModelPage
from .solver_type_page import SolverTypePage
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
LAST_PAGE = 7


class CaseWizard(QWizard):
    def __init__(self, parent, path: Path=None):
        super(CaseWizard, self).__init__(parent)

        self._meshProject = path is not None
        self._db = coredb.createDB()

        self._ui = Ui_CaseWizard()
        self._ui.setupUi(self)

        self.setPage(WORKSPACE, WorkspacePage(self, path))
        self.setPage(FLOW_TYPE, FlowTypePage(self))
        self.setPage(SOLVER_TYPE, SolverTypePage(self))
        self.setPage(MULTIPHASE_MODEL, MultiphaseModelPage(self))
        self.setPage(GRAVITY_MODEL, GravityModelPage(self))
        self.setPage(SPECIES_MODEL, SpeciesModelPage(self))
        self.setPage(LAST_PAGE, LastPage(self))
        self.setStartId(WORKSPACE)

        self.setSizeGripEnabled(True)
        self.setMaximumSize(800, 600)
        self.resize(620, 300)

    def isMeshProject(self):
        return self._meshProject

    def nextId(self):
        curId = self.currentId()
        if curId == WORKSPACE:
            return SOLVER_TYPE
        elif curId == SOLVER_TYPE:
            if self.field('solverTypePressureBased'):
                return MULTIPHASE_MODEL
            else:
                return LAST_PAGE
        elif curId == MULTIPHASE_MODEL:
            if self.field('multiphaseModel') == MultiphaseModel.OFF.value:
                return LAST_PAGE
            else:
                return GRAVITY_MODEL
        elif curId == GRAVITY_MODEL:
            return LAST_PAGE
        elif curId == LAST_PAGE:
            return LAST
        else:
            raise AssertionError('Unknown Case Wizard Page')

    def accept(self):
        generalXPath = '/general'
        gravityXPath = '/general/operatingConditions/gravity'
        modelsXPath = '/models'

        if self.field('solverTypePressureBased'):
            self._db.setValue(f'{generalXPath}/solverType', 'pressureBased')
            self._db.setValue(f'{generalXPath}/flowType', 'incompressible')
            self._db.setValue(f'{modelsXPath}/energyModels', 'off')
        else:
            self._db.setValue(f'{generalXPath}/solverType', 'densityBased')
            self._db.setValue(f'{generalXPath}/flowType', 'compressible')
            self._db.setValue(f'{modelsXPath}/energyModels', 'on')
            self._db.setValue(
                f'{NumericalDB.NUMERICAL_CONDITIONS_XPATH}/advanced/equations/energy/includeViscousDissipationTerms',
                'true')
            self._db.setValue(
                f'{NumericalDB.NUMERICAL_CONDITIONS_XPATH}/advanced/equations/energy/includeKineticEnergyTerms', 'true')
            self._db.setValue(
                f'{NumericalDB.NUMERICAL_CONDITIONS_XPATH}/advanced/equations/energy/includePressureWorkTerms', 'true')
            self._db.setValue(f'{MaterialDB.getXPathByName("air")}/density/specification', DensitySpecification.PERFECT_GAS.value)

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
