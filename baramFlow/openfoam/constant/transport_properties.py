#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import findSolver


class TransportProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'transportProperties')

        self._rname = rname
        self._db = CoreDBReader()

    def build(self):
        if self._data is not None:
            return self

        if findSolver() == 'interFoam':
            self._data = self._buildForInterFoam()
            return self

        # TransportProperties file is not used for now.
        # It may be used for Non-Newtonian fluid in the future
        return self

        self._data = {}

        mid = RegionDB.getMaterial(self._rname)
        dSpec = self._db.getValue(f'{MaterialDB.getXPath(mid)}/density/specification')
        vSpec = self._db.getValue(f'{MaterialDB.getXPath(mid)}/viscosity/specification')
        if dSpec == 'constant' and vSpec == 'constant':
            self._data['transportModel'] = 'Newtonian'

            density = self._db.getValue(f'{MaterialDB.getXPath(mid)}/density/constant')
            viscosity = self._db.getValue(f'{MaterialDB.getXPath(mid)}/viscosity/constant')

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

        baseMaterial = [(baseMaterialId, 1)]
        secondaryMatrerial = [(secondaryMaterialId, 1)]
        baseDensity = self._db.getDensity(baseMaterial, 0, 0)
        secondaryDensity = self._db.getDensity(secondaryMatrerial, 0, 0)

        baseViscosity = self._db.getViscosity(baseMaterial, 0)
        secondaryViscosity = self._db.getViscosity(secondaryMatrerial, 0)

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

