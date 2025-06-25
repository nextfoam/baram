#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import findSolver, allRoundSolver


class FvSchemes(DictionaryFile):
    def __init__(self, rname: str = ''):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(rname), 'fvSchemes')

        self._rname = rname
        self._db = CoreDBReader()
        self._mid = RegionDB.getMaterial(self._rname)

    def build(self):
        if self._data is not None:
            return self

        solver = findSolver()
        if solver == 'TSLAeroFoam' or solver == 'UTSLAeroFoam':
            self._generateTSLAero()
        else:
            phase = MaterialDB.getPhase(self._mid)
            if phase == 'solid':
                self._generateSolid()
            else:  # fluid
                self._generateFluid()

        return self

    def _generateTSLAero(self):
        self._data = {
            'ddtSchemes': {
                'default': 'backwardDualTime' if GeneralDB.isTimeTransient() else 'localEuler'
            },
            'gradSchemes': {
                'default': 'Gauss linear',
                'grad(k)':       'VKLimited Gauss linear 0.5',
                'grad(epsilon)': 'VKLimited Gauss linear 0.5',
                'grad(omega)':   'VKLimited Gauss linear 0.5',
                'grad(nuTilda)': 'VKLimited Gauss linear 0.5',
                'reconGrad':     'VKLimited Gauss linear 0.5'
            },
            'laplacianSchemes': self._constructLaplacianSchemes(),
            'interpolationSchemes': {
                'default': 'linear',
                'interpolate(rho)': 'linearUpwind phi grad(rho)'
            },
            'snGradSchemes': {
                'default': 'corrected'
            },
            'wallDist': {
                'method': 'meshWave'
            }
        }

        turbulentKineticEnergy = self._db.getValue('/numericalConditions/discretizationSchemes/turbulentKineticEnergy')
        if turbulentKineticEnergy == 'firstOrderUpwind':
            self._data['divSchemes'] = {
                'default': 'Gauss linear',
                'div(phi,k)':       'Gauss upwind',
                'div(phi,epsilon)': 'Gauss upwind',
                'div(phi,omega)':   'Gauss upwind',
                'div(phi,nuTilda)': 'Gauss upwind'
            }
        elif turbulentKineticEnergy == 'secondOrderUpwind':
            self._data['divSchemes'] = {
                'default': 'Gauss linear',
                'div(phi,k)':       'Gauss linearUpwind reconGrad',
                'div(phi,epsilon)': 'Gauss linearUpwind reconGrad',
                'div(phi,omega)':   'Gauss linearUpwind reconGrad',
                'div(phi,nuTilda)': 'Gauss linearUpwind reconGrad'
            }

        return self

    def _generateSolid(self):
        self._data = {
            'ddtSchemes': self._constructDdtSchemes(),
            'gradSchemes': {
                'default': 'Gauss linear'
            },
            'divSchemes': {
                'default': 'Gauss linear'
            },
            'laplacianSchemes': self._constructLaplacianSchemes(),
            'interpolationSchemes': {
                'default': 'linear'
            },
            'snGradSchemes': {
                'default': 'corrected'
            }
        }

    def _generateFluid(self):
        self._data = {
            'ddtSchemes': self._constructDdtSchemes(),
            'gradSchemes': self._constructGradSchemes(),
            'divSchemes': self._constructDivSchemes(),
            'laplacianSchemes': self._constructLaplacianSchemes(),
            'interpolationSchemes': {
                'default': 'linear',
                'interpolate(p)':     self._db.getValue('/numericalConditions/discretizationSchemes/pressure'),
                'interpolate(p_rgh)': self._db.getValue('/numericalConditions/discretizationSchemes/pressure'),
                'reconstruct(psi)': 'Minmod',
                'reconstruct(p)':   'Minmod',
                'reconstruct(U)':   'MinmodV',
                'reconstruct(Dp)':  'Minmod'
            },
            'snGradSchemes': {
                'default': 'corrected'
            },
            'wallDist': {
                'method': 'meshWave'
            }
        }

    def _constructDdtSchemes(self):
        time = self._db.getValue('/numericalConditions/discretizationSchemes/time')

        ddtSchemes = {}
        if GeneralDB.isTimeTransient():
            if time == 'firstOrderImplicit':
                ddtSchemes = {
                    'default': 'Euler'
                }
            elif time == 'secondOrderImplicit':
                ddtSchemes = {
                    'default': 'backward'
                }
        else:
            if allRoundSolver():  # this solver is able to solve both steady and transient
                ddtSchemes = {
                    'default': 'localEuler'
                }
            else:
                ddtSchemes = {
                    'default': 'steadyState'
                }

        return ddtSchemes

    def _constructGradSchemes(self):
        return {
            'default': 'Gauss linear',
            'momentumReconGrad':   'VKLimited Gauss linear 1.0',
            'energyReconGrad':     'VKLimited Gauss linear 1.0',
            'turbulenceReconGrad': 'VKLimited Gauss linear 1.0'
        }

    def _constructDivSchemes(self):
        energyModel = self._db.getValue('/models/energyModels')
        multiphaseModel = self._db.getValue('/models/multiphaseModels/model')
        speciesModel = self._db.getValue('/models/speciesModels')

        momentum = self._db.getValue('/numericalConditions/discretizationSchemes/momentum')
        energy = self._db.getValue('/numericalConditions/discretizationSchemes/energy')
        turbulentKineticEnergy = self._db.getValue('/numericalConditions/discretizationSchemes/turbulentKineticEnergy')
        volumeFraction = self._db.getValue('/numericalConditions/discretizationSchemes/volumeFraction')

        # prepend 'bounded' prefix for steady-only solvers
        if not GeneralDB.isTimeTransient() and not allRoundSolver():
            bounded = 'bounded '
        else:
            bounded = ''

        divSchemes = {
            'default': 'Gauss linear',
            'div(phi,age)': 'bounded Gauss linearUpwind momentumReconGrad'
        }

        if momentum == 'firstOrderUpwind':
            divSchemes.update({
                'div(phi,U)': f'{bounded}Gauss upwind',
                'div(rhoPhi,U)': f'{bounded}Gauss upwind',
                'div(phiNeg,U)': f'{bounded}Gauss upwind',
                'div(phiPos,U)': f'{bounded}Gauss upwind'
            })
        elif momentum == 'secondOrderUpwind':
            divSchemes.update({
                'div(phi,U)': f'{bounded}Gauss linearUpwind momentumReconGrad',
                'div(rhoPhi,U)': f'{bounded}Gauss linearUpwind momentumReconGrad',
                'div(phiNeg,U)': f'{bounded}Gauss MinmodV',
                'div(phiPos,U)': f'{bounded}Gauss MinmodV'
            })

        if turbulentKineticEnergy == 'firstOrderUpwind':
            divSchemes.update({
                'div(phi,k)': f'{bounded}Gauss upwind',
                'div(phi,epsilon)': f'{bounded}Gauss upwind',
                'div(phi,omega)': f'{bounded}Gauss upwind',
                'div(phi,nuTilda)': f'{bounded}Gauss upwind'
            })
        elif turbulentKineticEnergy == 'secondOrderUpwind':
            divSchemes.update({
                'div(phi,k)': f'{bounded}Gauss linearUpwind turbulenceReconGrad',
                'div(phi,epsilon)': f'{bounded}Gauss linearUpwind turbulenceReconGrad',
                'div(phi,omega)': f'{bounded}Gauss linearUpwind turbulenceReconGrad',
                'div(phi,nuTilda)': f'{bounded}Gauss linearUpwind turbulenceReconGrad'
            })

        if energyModel != 'off':
            if energy == 'firstOrderUpwind':
                divSchemes.update({
                    'div(phi,h)': f'{bounded}Gauss upwind',
                    'div(phiNeg,h)': f'{bounded}Gauss upwind',
                    'div(phiPos,h)': f'{bounded}Gauss upwind',
                    'div(phi,K)': f'{bounded}Gauss upwind',
                    'div(phiNeg,K)': f'{bounded}Gauss upwind',
                    'div(phiPos,K)': f'{bounded}Gauss upwind'
                })
            elif energy == 'secondOrderUpwind':
                divSchemes.update({
                    'div(phi,h)': f'{bounded}Gauss linearUpwind energyReconGrad',
                    'div(phiNeg,h)': f'{bounded}Gauss Minmod',
                    'div(phiPos,h)': f'{bounded}Gauss Minmod',
                    'div(phi,K)': f'{bounded}Gauss linearUpwind energyReconGrad',
                    'div(phiNeg,K)': f'{bounded}Gauss Minmod',
                    'div(phiPos,K)': f'{bounded}Gauss Minmod',
                    'div(phid_neg,p)': f'{bounded}Gauss Minmod',
                    'div(phid_pos,p)': f'{bounded}Gauss Minmod'
                })

        if multiphaseModel != 'off':
            if volumeFraction == 'firstOrderUpwind':
                divSchemes.update({
                    'div(phi,alpha)': f'{bounded}Gauss upwind',
                    'div(phirb,alpha)': f'{bounded}Gauss upwind'
                })
            elif volumeFraction == 'secondOrderUpwind':
                divSchemes.update({
                    'div(phi,alpha)': f'{bounded}Gauss vanLeer',
                    'div(phirb,alpha)': f'{bounded}Gauss linear'
                })

        if self._db.getValue(f'{NumericalDB.NUMERICAL_CONDITIONS_XPATH}/discretizationSchemes/scalar') == 'firstOrderUpwind':
            divSchemes['div(phi,scalar)'] = f'{bounded}Gauss upwind'
        else:
            divSchemes['div(phi,scalar)'] = f'{bounded}Gauss linearUpwind momentumReconGrad'

        if ModelsDB.isSpeciesModelOn():
            if self._db.getValue(f'{NumericalDB.NUMERICAL_CONDITIONS_XPATH}/discretizationSchemes/species') == 'firstOrderUpwind':
                speciesDivSchemes = f'{bounded}Gauss upwind'
            else:
                speciesDivSchemes = f'{bounded}Gauss linearUpwind momentumReconGrad'

            for specie in MaterialDB.getSpecies(self._mid).values():
                divSchemes[f'div(phi,{specie})'] = speciesDivSchemes

        return divSchemes

    def _constructLaplacianSchemes(self):
        laplacianSchemes = {}

        relaxationDisabled = self._db.getAttribute('/numericalConditions/highOrderTermRelaxation', 'disabled')
        relFactor = self._db.getValue('/numericalConditions/highOrderTermRelaxation/relaxationFactor')
        if relaxationDisabled == 'true':
            laplacianSchemes['default'] = 'Gauss linear corrected'
        else:
            laplacianSchemes['default'] = f'Gauss linear limited corrected {relFactor}'

        return laplacianSchemes
