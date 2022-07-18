#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.material_db import MaterialDB
from openfoam.dictionary_file import DictionaryFile


class TransportProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'transportProperties')

        self._rname = rname
        self._db = coredb.CoreDB()

    def build(self):
        if self._data is not None:
            return self
        self._data = {}

        mid = self._db.getValue(f'.//regions/region[name="{self._rname}"]/material')

        energyModels = self._db.getValue('.//models/energyModels')
        dSpec = self._db.getValue(f'{MaterialDB.getXPath(mid)}/density/specification')
        vSpec = self._db.getValue(f'{MaterialDB.getXPath(mid)}/viscosity/specification')

        if energyModels == "off" and dSpec == 'constant' and vSpec == 'constant':
            self._data['transportModel'] = 'Newtonian'

            density = self._db.getValue(f'{MaterialDB.getXPath(mid)}/density/constant')
            viscosity = self._db.getValue(f'{MaterialDB.getXPath(mid)}/viscosity/constant')

            nu = float(viscosity) / float(density)
            self._data['nu'] = f'[ 0 2 -1 0 0 0 0 ] {nu}'

            # MultiPhase (not defined yet)
            # multiphaseModels = self._db.getValue('.//models/multiphaseModels')
            # if multiphaseModels == "VOF":
            #     self._data['VOF'] = {
            #         'phases': '(liquid gas)',
            #         'sigma': f'{self.surfaceTensionTension}',
            #         'liquid': {
            #             'transportModel': 'Newtonian',
            #             'nu': f'{self.liquidNu}',
            #             'rho': f'{self.liquidRho}'
            #         },
            #         'gas': {
            #             'transportModel': 'Newtonian',
            #             'nu': f'{self.gasNu}',
            #             'rho': f'{self.gasRho}'
            #         }
            #     }
            # elif multiphaseModels == 'Cavitation':
            #     self._data['Cavitation'] = {
            #         'phases': '(liquid gas)',
            #         'phaseChangeTwoPhaseMixture': f'{self.cavitationModel}',
            #         'pSat': f'{self.pSat}',
            #         'sigma': f'{self.surfaceTension}',
            #         'liquid': {
            #             'transportModel': 'Newtonian',
            #             'nu': f'{self.liquidNu}',
            #             'rho': f'{self.liquidRho}'
            #         },
            #         'gas': {
            #             'transportModel': 'Newtonian',
            #             'nu': f'{self.gasNu}',
            #             'rho': f'{self.gasRho}'
            #         },
            #
            #         'UInf': f'{self.uInf}',
            #         'tInf': f'{self.tInt}',
            #         'dNuc': f'{self.dNuc}',
            #         'n': f'{self.n}',
            #         'aNuc': f'{self.aNuc}',
            #         'Cc': f'{self.cc}',
            #         'Cv': f'{self.cv}'
            #     }

        return self
