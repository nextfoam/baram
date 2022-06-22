#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from coredb import coredb
from view.setup.models.models_db import ModelsDB, TurbulenceModel, KEpsilonModel, KOmegaModel


class TurbulenceProperties(object):
    def __init__(self, rname: str):
        self._rname = rname
        self._data = None

    def __str__(self):
        return self.asstr()

    def _build(self):
        if self._data is not None:
            return

        db = coredb.CoreDB()

        model = ModelsDB.getTurbulenceModel()
        if model == TurbulenceModel.INVISCID or model == TurbulenceModel.LAMINAR:
            self._constructLaminarProperties()
        elif model == TurbulenceModel.SPALART_ALLMARAS:
            self._constructRASproperties('SpalartAllmaras')
        elif model == TurbulenceModel.K_EPSILON:
            subModel = db.getValue(ModelsDB.TURBULENCE_MODELS_PATH + '/k-epsilon/model')
            if subModel == KEpsilonModel.STANDARD.value:
                self._constructRASproperties('kEpsilon')
            elif subModel == KEpsilonModel.RNG.value:
                self._constructRASproperties('RNGkEpsilon')
            elif subModel == KEpsilonModel.REALIZABLE.value:
                self._constructRASproperties('realizableKE')
        elif model == TurbulenceModel.K_OMEGA:
            subModel = db.getValue(ModelsDB.TURBULENCE_MODELS_PATH + '/k-omega/model')
            if subModel == KOmegaModel.SST.value:
                self._constructRASproperties('kOmegaSST')
        elif model == TurbulenceModel.LES:
            self._constructLESProperties()

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

    def asdict(self):
        self._build()
        return self._data

    def asstr(self):
        HEADER = {
            'version': '2.0',
            'format': 'ascii',
            'class': 'dictionary',
            'location': f'constant/{self._rname}',
            'object': 'turbulenceProperties'
        }
        self._build()
        return str(FoamFileGenerator(self._data, header=HEADER))
