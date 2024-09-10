#!/usr/bin/env python
# -*- coding: utf-8 -*-

from itertools import combinations
from typing import Optional

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import ViscositySpecification
from baramFlow.coredb.region_db import RegionDB, CavitationModel
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

        solver = findSolver()
        if solver == 'interFoam':
            self._data = self._buildForInterFoam()
            return self

        elif solver == 'multiphaseInterFoam':
            self._data = self._buildForMultiphaseInterFoam()
            return self

        if solver == 'interPhaseChangeFoam' or solver == 'interPhaseChangeDyMFoam':
            self._data = self._buildForInterPhaseChangeFoam()
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
        materials = RegionDB.getSecondaryMaterials(self._rname)
        if len(materials) == 0:  # It is not MULTI-phase
            return None

        # * "interFoam" supports only one secondary material
        # * primary material should go last
        materials = [materials[0], RegionDB.getMaterial(self._rname)]

        phases = []
        data = {
            'phases': phases,
        }

        for mid in materials:
            name = MaterialDB.getName(mid)
            phases.append(name)
            data[name] = self._buildMaterial(mid)

        tensions = dict([((mid1, mid2), tension) for mid1, mid2, tension in self._db.getSurfaceTensions(self._rname)])
        if (materials[0], materials[1]) in tensions:
            t = tensions[(materials[0], materials[1])]
        elif (materials[1], materials[0]) in tensions:
            t = tensions[(materials[1], materials[0])]
        else:
            t = 0

        data['sigma'] = t

        return data

    def _buildForMultiphaseInterFoam(self) -> Optional[dict]:
        materials = RegionDB.getSecondaryMaterials(self._rname)
        if len(materials) == 0:  # It is not MULTI-phase
            return None

        # primary material may locate at first.
        # "nAlphaSubCycles" seems to treat the first material as reference
        mid = RegionDB.getMaterial(self._rname)
        materials.insert(0, mid)

        phases = []

        for mid in materials:
            name = MaterialDB.getName(mid)
            phases.append((name, self._buildMaterial(mid)))

        sigmas = []

        tensions = dict([((mid1, mid2), tension) for mid1, mid2, tension in self._db.getSurfaceTensions(self._rname)])

        for mid1, mid2 in combinations(materials, 2):
            if (mid1, mid2) in tensions:
                t = tensions[(mid1, mid2)]
            elif (mid2, mid1) in tensions:
                t = tensions[(mid2, mid1)]
            else:
                t = 0

            sigmas.append(([MaterialDB.getName(mid1), MaterialDB.getName(mid2)], t))

        data = {
            'phases': phases,
            'sigmas': sigmas
        }

        return data

    def _buildForInterPhaseChangeFoam(self) -> Optional[dict]:
        materials = RegionDB.getSecondaryMaterials(self._rname)
        if len(materials) != 1:
            return None

        # * "interFoam" supports only one secondary material
        # * primary material should go last
        materials = [materials[0], RegionDB.getMaterial(self._rname)]

        cavitationXPath = RegionDB.getXPath(self._rname) + '/phaseInteractions/massTransfers/massTransfer[mechanism="cavitation"]/cavitation'
        cavitationModel = CavitationModel(self._db.getValue(cavitationXPath + '/model'))

        tensions = dict([((mid1, mid2), tension) for mid1, mid2, tension in self._db.getSurfaceTensions(self._rname)])
        if (materials[0], materials[1]) in tensions:
            t = tensions[(materials[0], materials[1])]
        elif (materials[1], materials[0]) in tensions:
            t = tensions[(materials[1], materials[0])]
        else:
            t = 0

        phases = []
        data = {
            'phases': phases,
            'pSat': self._db.getValue(cavitationXPath + '/vaporizationPressure'),
            'sigma': t
        }

        for mid in materials:
            name = MaterialDB.getName(mid)
            phases.append(name)
            data[name] = self._buildMaterial(mid)

        constantsXPath = f'{cavitationXPath}/{cavitationModel.value}'
        if cavitationModel == CavitationModel.SCHNERR_SAUER:
            data['phaseChangeTwoPhaseMixture'] ='SchnerrSauer'
            data['SchnerrSauerCoeffs'] = {
                'n':self._db.getValue(constantsXPath + '/bubbleNumberDensity'),
                'dNuc': self._db.getValue(constantsXPath + '/bubbleDiameter'),
                'Cc': self._db.getValue(constantsXPath + '/evaporationCoefficient'),
                'Cv': self._db.getValue(constantsXPath + '/condensationCoefficient')
            }
        elif cavitationModel == CavitationModel.KUNZ:
            data['phaseChangeTwoPhaseMixture'] ='Kunz'
            data['KunzCoeffs'] = {
                'UInf':self._db.getValue(constantsXPath + '/freeStreamVelocity'),
                'tInf': self._db.getValue(constantsXPath + '/meanFlowTimeScale'),
                'Cc': self._db.getValue(constantsXPath + '/evaporationCoefficient'),
                'Cv': self._db.getValue(constantsXPath + '/condensationCoefficient')
            }
        elif cavitationModel == CavitationModel.MERKLE:
            data['phaseChangeTwoPhaseMixture'] ='Merkle'
            data['MerkleCoeffs'] = {
                'UInf':self._db.getValue(constantsXPath + '/freeStreamVelocity'),
                'tInf': self._db.getValue(constantsXPath + '/meanFlowTimeScale'),
                'Cc': self._db.getValue(constantsXPath + '/evaporationCoefficient'),
                'Cv': self._db.getValue(constantsXPath + '/condensationCoefficient')
            }
        elif cavitationModel == CavitationModel.ZWART_GERBER_BELAMRI:
            data['phaseChangeTwoPhaseMixture'] ='Zwart'
            data['ZwartCoeffs'] = {
                'aNuc':self._db.getValue(constantsXPath + '/nucleationSiteVolumeFraction'),
                'dNuc': self._db.getValue(constantsXPath + '/bubbleDiameter'),
                'Cc': self._db.getValue(constantsXPath + '/evaporationCoefficient'),
                'Cv': self._db.getValue(constantsXPath + '/condensationCoefficient')
            }

        return data

    def _buildMaterial(self, mid):
        xpath = MaterialDB.getXPath(mid)

        density = self._db.getDensity([(mid, 1)], 0, 0)
        viscositySpecification = ViscositySpecification(self._db.getValue(xpath + '/viscosity/specification'))

        if viscositySpecification == ViscositySpecification.CROSS_POWER_LAW:
            return {
                'transportModel': 'CrossPowerLaw',
                'CrossPowerLawCoeffs': {
                    'nu0': self._db.getValue(xpath + '/viscosity/cross/zeroShearViscosity'),
                    'nuInf': self._db.getValue(xpath + '/viscosity/cross/infiniteShearViscosity'),
                    'm': self._db.getValue(xpath + '/viscosity/cross/naturalTime'),
                    'n': self._db.getValue(xpath + '/viscosity/cross/powerLawIndex')
                },
                'rho': density
            }

        if viscositySpecification == ViscositySpecification.HERSCHEL_BULKLEY:
            return {
                'transportModel': 'HerschelBulkley',
                'HerschelBulkleyCoeffs': {
                    'nu0': self._db.getValue(xpath + '/viscosity/herschelBulkley/zeroShearViscosity'),
                    'tau0': self._db.getValue(xpath + '/viscosity/herschelBulkley/yieldStressThreshold'),
                    'k': self._db.getValue(xpath + '/viscosity/herschelBulkley/consistencyIndex'),
                    'n': self._db.getValue(xpath + '/viscosity/herschelBulkley/powerLawIndex')
                },
                'rho': density
            }

        if viscositySpecification == ViscositySpecification.BIRD_CARREAU:
            return {
                'transportModel': 'BirdCarreau',
                'BirdCarreauCoeffs': {
                    'nu0': self._db.getValue(xpath + '/viscosity/carreau/zeroShearViscosity'),
                    'nuInf': self._db.getValue(xpath + '/viscosity/carreau/infiniteShearViscosity'),
                    'k': self._db.getValue(xpath + '/viscosity/carreau/relaxationTime'),
                    'n': self._db.getValue(xpath + '/viscosity/carreau/powerLawIndex'),
                    'a': self._db.getValue(xpath + '/viscosity/carreau/linearityDeviation')
                },
                'rho': density
            }

        if viscositySpecification == ViscositySpecification.POWER_LAW:
            return {
                'transportModel': 'powerLaw',
                'powerLawCoeffs': {
                    'nuMax': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/maximumViscosity'),
                    'nuMin': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/minimumViscosity'),
                    'k': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/consistencyIndex'),
                    'n': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/powerLawIndex')
                },
                'rho': density
            }

        viscosity = self._db.getViscosity([(mid, 1)], 0)
        nu = viscosity / density

        return {
            'transportModel': 'Newtonian',
            'nu': nu,
            'rho': density
        }
