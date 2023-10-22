#!/usr/bin/env python
# -*- coding: utf-8 -*-


from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb import coredb
import baramFlow.openfoam.solver
from baramFlow.openfoam.file_system import FileSystem


class FvSchemes(DictionaryFile):
    def __init__(self, rname: str = ''):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(rname), 'fvSchemes')

        self._rname = rname
        self._db = coredb.CoreDB()
        self._cap = None

        self.relaxationDisabled = self._db.getAttribute('.//numericalConditions/highOrderTermRelaxation', 'disabled')
        self.relFactor = self._db.getValue('.//numericalConditions/highOrderTermRelaxation/relaxationFactor')

    def build(self):
        if self._data is not None:
            return self

        solvers = baramFlow.openfoam.solver.findSolvers()
        if len(solvers) != 1:  # configuration not enough yet
            raise RuntimeError

        solver = solvers[0]
        self._cap = baramFlow.openfoam.solver.getSolverCapability(solver)

        mid = self._db.getValue(f'.//region[name="{self._rname}"]/material')
        phase = self._db.getValue(f'.//materials/material[@mid="{mid}"]/phase')

        if solver == 'TSLAeroFoam':
            self._generateTSLAero()
        else:
            if phase == 'solid':
                self._generateSolid()
            else:  # fluid
                self._generateFluid()

        return self

    def _generateTSLAero(self):
        self._data = {
            'ddtSchemes': {
                'default': 'localEuler'
            },
            'gradSchemes': {
                'default': 'Gauss linear',
                'grad(k)':       'VKMDLimited Gauss linear 0.5',
                'grad(epsilon)': 'VKMDLimited Gauss linear 0.5',
                'grad(omega)':   'VKMDLimited Gauss linear 0.5',
                'grad(nuTilda)': 'VKMDLimited Gauss linear 0.5',
                'reconGrad':     'VKMDLimited Gauss linear 0.5'
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

        turbulentKineticEnergy = self._db.getValue('.//discretizationSchemes/turbulentKineticEnergy')
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
                'interpolate(p)':     'momentumWeightedReconstruct',
                'interpolate(p_rgh)': 'momentumWeightedReconstruct',
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
        timeTransient = self._db.getValue('.//general/timeTransient')
        time = self._db.getValue('.//discretizationSchemes/time')

        ddtSchemes = {}
        if timeTransient == 'true':
            if time == 'firstOrderImplicit':
                ddtSchemes = {
                    'default': 'Euler'
                }
            elif time == 'secondOrderImplicit':
                ddtSchemes = {
                    'default': 'backward'
                }
        else:
            if self._cap['timeTransient']:  # this solver is able to solve both steady and transient
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
            'energyReconGrad':     'BJLimited Gauss linear 1.0',
            'turbulenceReconGrad': 'BJLimited Gauss linear 1.0'
        }

    def _constructDivSchemes(self):
        energyModel = self._db.getValue('.//models/energyModels')
        multiphaseModel = self._db.getValue('.//models/multiphaseModels/model')
        speciesModel = self._db.getValue('.//models/speciesModels')

        momentum = self._db.getValue('.//discretizationSchemes/momentum')
        energy = self._db.getValue('.//discretizationSchemes/energy')
        turbulentKineticEnergy = self._db.getValue('.//discretizationSchemes/turbulentKineticEnergy')
        volumeFraction = self._db.getValue('.//discretizationSchemes/volumeFraction')

        # prepend 'bounded' prefix for steady state solvers
        if self._cap['timeSteady'] and not self._cap['timeTransient']:
            bounded = 'bounded '
        else:
            bounded = ''

        divSchemes = {
            'default': 'Gauss linear'
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

        # unlike other values, do not add 'bounded' for species schemes even for steady state solvers
        if speciesModel != 'off':
            pass  # Not implemented yet

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

        return divSchemes

    def _constructLaplacianSchemes(self):
        laplacianSchemes = {}

        if self.relaxationDisabled == 'true':
            laplacianSchemes['default'] = 'Gauss linear corrected'
        else:
            laplacianSchemes['default'] = f'Gauss linear limited corrected {self.relFactor}'

        return laplacianSchemes
