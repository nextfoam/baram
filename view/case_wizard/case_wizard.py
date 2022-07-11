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

        self.setPage(self.Page.FLOW_TYPE.value, FlowTypePage(self))
        self.setPage(self.Page.SOLVER_TYPE.value, SolverTypePage(self))
        self.setPage(self.Page.ENERGY_MODEL.value, EnergyModelPage(self))
        self.setPage(self.Page.MULTIPHASE_MODEL.value, MultiphaseModelPage(self))
        self.setPage(self.Page.GRAVITY_MODEL.value, GravityModelPage(self))
        self.setPage(self.Page.SPECIES_MODEL.value, SpeciesModelPage(self))
        self.setStartId(self.Page.FLOW_TYPE.value)

        self.accepted.connect(self.caseAccepted)

    def nextId(self):
        curID = self.currentId()
        if curID == self.Page.FLOW_TYPE.value:
            if self.field('flowTypeCompressible'):
                return self.Page.SOLVER_TYPE.value
            else:
                return self.Page.ENERGY_MODEL.value
        elif curID == self.Page.SOLVER_TYPE.value:
            return self.Page.SPECIES_MODEL.value
        elif curID == self.Page.ENERGY_MODEL.value:
            if self.field('energyModelsInclude'):
                return self.Page.GRAVITY_MODEL.value
            else:
                return self.Page.MULTIPHASE_MODEL.value
        elif curID == self.Page.MULTIPHASE_MODEL.value:
            if self.field('multiphaseModelsInclude'):
                return self.Page.GRAVITY_MODEL.value
            else:
                return self.Page.SPECIES_MODEL.value
        elif curID == self.Page.GRAVITY_MODEL.value:
            return self.Page.SPECIES_MODEL.value

        elif curID == self.Page.SPECIES_MODEL.value:
            return self.Page.LAST.value
        else:
            raise NotImplementedError('Unknown Case Wizard Page')

    def caseAccepted(self):
        general_path = './/general'
        models_path = './/models'

        if self.field('flowTypeCompressible'):
            self._db.setValue(f'{general_path}/flowType', 'compressible')
        else:
            self._db.setValue(f'{general_path}/flowType', 'incompressible')

        if self.field('solverTypePressureBased'):
            self._db.setValue(f'{general_path}/solverType', 'pressureBased')
        else:
            self._db.setValue(f'{general_path}/solverType', 'densityBased')

        if self.field('energyModelsInclude'):
            self._db.setValue(f'{models_path}/energyModels', 'on')
        else:
            self._db.setValue(f'{models_path}/energyModels', 'off')

        if self.field('multiphaseModelsInclude'):
            self._db.setValue(f'{models_path}/multiphaseModels/model', 'on')
        else:
            self._db.setValue(f'{models_path}/multiphaseModels/model', 'off')

        gravity_path = f'{general_path}/operatingConditions/gravity'
        if self.field('gravityInclude'):
            self._db.setAttribute(f'{gravity_path}', 'disabled', 'false')
            self._db.setValue(f'{gravity_path}/direction/x', self.field('gravityX'))
            self._db.setValue(f'{gravity_path}/direction/y', self.field('gravityY'))
            self._db.setValue(f'{gravity_path}/direction/z', self.field('gravityZ'))
        else:
            self._db.setAttribute(f'{gravity_path}', 'disabled', 'true')

        if self.field('speciesModelsInclude'):
            self._db.setValue(f'{models_path}/speciesModels', 'on')
        else:
            self._db.setValue(f'{models_path}/speciesModels', 'off')
