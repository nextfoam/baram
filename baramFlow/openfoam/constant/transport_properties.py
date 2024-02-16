#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.region_db import RegionDB
import baramFlow.openfoam.solver
from baramFlow.openfoam.file_system import FileSystem


class TransportProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'transportProperties')

        self._rname = rname
        self._db = coredb.CoreDB()

    def build(self):
        if self._data is not None:
            return self

        solvers = baramFlow.openfoam.solver.findSolvers()
        if len(solvers) == 1 and solvers[0] == 'interFoam':
            self._data = self._buildForInterFoam()
            return self

        self._data = {}

        mid = self._db.retrieveValue(f'.//regions/region[name="{self._rname}"]/material')

        energyModels = self._db.retrieveValue('.//models/energyModels')
        dSpec = self._db.retrieveValue(f'{MaterialDB.getXPath(mid)}/density/specification')
        vSpec = self._db.retrieveValue(f'{MaterialDB.getXPath(mid)}/viscosity/specification')

        if energyModels == "off" and dSpec == 'constant' and vSpec == 'constant':
            self._data['transportModel'] = 'Newtonian'

            density = self._db.retrieveValue(f'{MaterialDB.getXPath(mid)}/density/constant')
            viscosity = self._db.retrieveValue(f'{MaterialDB.getXPath(mid)}/viscosity/constant')

            nu = float(viscosity) / float(density)
            self._data['nu'] = f'[ 0 2 -1 0 0 0 0 ] {nu}'

        return self

    def _buildForInterFoam(self) -> Optional[dict]:
        secondaryMaterials = RegionDB.getSecondaryMaterials(self._rname)
        if len(secondaryMaterials) == 0:
            return None

        baseMaterialId = RegionDB.getMaterial(self._rname)
        secondaryMaterialId = secondaryMaterials[0]  # "interFoam" can handle only two phases

        baseMaterialName = MaterialDB.getName(baseMaterialId)
        secondaryMaterialName = MaterialDB.getName(secondaryMaterialId)

        # temperature and pressure are used because interFoam works only when energy off
        #     i.e. constant density and viscosity

        baseDensity = MaterialDB.getDensity(baseMaterialId, 0, 0)
        secondaryDensity = MaterialDB.getDensity(secondaryMaterialId, 0, 0)

        baseViscosity = MaterialDB.getViscosity(baseMaterialId, 0)
        secondaryViscosity = MaterialDB.getViscosity(secondaryMaterialId, 0)

        baseNu = baseViscosity / baseDensity
        secondaryNu = secondaryViscosity / secondaryDensity

        surfaceTension = None
        surfaceTensions = self._db.getSurfaceTensions(self._rname)
        for mid1, mid2, tension in surfaceTensions:
            if mid1 == baseMaterialId or mid2 == baseMaterialId:
                surfaceTension = tension
                break  # "interFoam" handles only two phases

        if surfaceTension is None:
            return None

        data = {
            'phases': [secondaryMaterialName, baseMaterialName],
            secondaryMaterialName: {
                'transportModel': 'Newtonian',
                'nu': secondaryNu,
                'rho': secondaryDensity
            },
            baseMaterialName: {
                'transportModel': 'Newtonian',
                'nu': baseNu,
                'rho': baseDensity
            },
            'sigma': surfaceTension
        }

        return data

