#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.models_db import ModelsDB, TurbulenceModel, KEpsilonModel, KOmegaModel
from openfoam.dictionary_file import DictionaryFile


class TurbulenceProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'TurbulenceProperties')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()

        model = ModelsDB.getTurbulenceModel()
        if model == TurbulenceModel.INVISCID or model == TurbulenceModel.LAMINAR:
            self._constructLaminarProperties()
        elif model == TurbulenceModel.SPALART_ALLMARAS:
            self._constructRASproperties('SpalartAllmaras')
        elif model == TurbulenceModel.K_EPSILON:
            subModel = db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/model')
            if subModel == KEpsilonModel.STANDARD.value:
                self._constructRASproperties('kEpsilon')
            elif subModel == KEpsilonModel.RNG.value:
                self._constructRASproperties('RNGkEpsilon')
            elif subModel == KEpsilonModel.REALIZABLE.value:
                self._constructRASproperties('realizableKE')
        elif model == TurbulenceModel.K_OMEGA:
            subModel = db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/k-omega/model')
            if subModel == KOmegaModel.SST.value:
                self._constructRASproperties('kOmegaSST')
        elif model == TurbulenceModel.LES:
            self._constructLESProperties()

        return self

    def _constructLaminarProperties(self):
        self._data = {
            'simulationType': 'laminar'
        }

    def _constructRASproperties(self, model):
        self._data = {
            'simulationType': 'RAS',
            'RAS': {
                'RASModel': model,
                'turbulence': 'on',
                'printCoeffs': 'on',
            }
        }

    def _constructLESProperties(self):
        self._data = {
            'simulationType': 'LES'
        }
