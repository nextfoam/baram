#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.materials.material_db import MaterialDB
from openfoam.dictionary_file import DictionaryFile


class TransportProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'transportProperties')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return

        db = coredb.CoreDB()
        energyModels = db.getValue('.//models/energyModels')

        self._data = {}
        if energyModels == "off":
            self._data['transportModel'] = 'Newtonian'

            mid = db.getValue(f'.//region[name="{self._rname}"]/material')
            density = db.getValue(f'{MaterialDB.getXPath(mid)}/density')
            viscosity = db.getValue(f'{MaterialDB.getXPath(mid)}/viscosity')
            nu = viscosity / density
            self._data['nu'] = f'[ 0 2 -1 0 0 0 0 ] {nu}'

            # MultiPhase (not defined yet)
            # multiphaseModels = db.getValue('.//models/multiphaseModels')
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
