#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.app import app
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel, KEpsilonModel, KOmegaModel, NearWallTreatment
from baramFlow.openfoam.file_system import FileSystem


class TurbulenceProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'turbulenceProperties')

        self._rname = rname
        self._db = app.case.db
        self._model = ModelsDB.getTurbulenceModel()

    def build(self):
        if self._data is not None:
            return self

        if self._model == TurbulenceModel.INVISCID or self._model == TurbulenceModel.LAMINAR:
            self._constructLaminarProperties()
        elif self._model == TurbulenceModel.SPALART_ALLMARAS:
            self._constructRASproperties('SpalartAllmaras')
        elif self._model == TurbulenceModel.K_EPSILON:
            subModel = self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/model')
            if subModel == KEpsilonModel.STANDARD.value:
                self._constructRASproperties('kEpsilon')
            elif subModel == KEpsilonModel.RNG.value:
                self._constructRASproperties('RNGkEpsilon')
            elif subModel == KEpsilonModel.REALIZABLE.value:
                treatment = self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/nearWallTreatment')
                if treatment == NearWallTreatment.ENHANCED_WALL_TREATMENT.value:
                    self._constructRASproperties('realizableKEtwoLayer')
                elif treatment == NearWallTreatment.STANDARD_WALL_FUNCTIONS.value:
                    self._constructRASproperties('realizableKE')
                else:
                    raise RuntimeError
        elif self._model == TurbulenceModel.K_OMEGA:
            subModel = self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/k-omega/model')
            if subModel == KOmegaModel.SST.value:
                self._constructRASproperties('kOmegaSST')
        elif self._model == TurbulenceModel.LES:
            self._constructLESProperties()

        return self

    def _constructLaminarProperties(self):
        self._data = {
            'simulationType': 'laminar'
        }

    def _constructRASproperties(self, subModel):
        self._data = {
            'simulationType': 'RAS',
            'RAS': {
                'RASModel': subModel,
                'turbulence': 'on',
                'printCoeffs': 'on',
                'Prt': self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/energyPrandtlNumber')
            }
        }

        hasABLInlet = False
        boundaries = self._db.getBoundaryConditions(self._rname)
        for _, _, type_ in boundaries:
            if type_ == 'ablInlet':
                hasABLInlet = True
                break

        if hasABLInlet and self._model == TurbulenceModel.K_EPSILON:
            self._data['RAS']['kEpsilonCoeffs'] = {
                'Cmu': 0.09,
                'C1': 1.44,
                'C2': 1.92,
                'sigmaEps': 1.11
            }

        if subModel == 'realizableKEtwoLayer':
            self._data['RAS']['ReyStar'] = self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/threshold')
            self._data['RAS']['deltaRey'] = self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/blendingWidth')

    def _constructLESProperties(self):
        self._data = {
            'simulationType': 'LES'
        }
