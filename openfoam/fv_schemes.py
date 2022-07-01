#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from coredb import coredb

import openfoam.solver


class FvSchemes(object):
    def __init__(self, rname: str):
        self._rname = rname
        self._data = None
        self._db = coredb.CoreDB()
        solvers = openfoam.solver.findSolvers()
        if len(solvers) != 1:  # configuration not enough yet
            raise RuntimeError

        print(solvers)
        self._solver = solvers[0]
        self._cap = openfoam.solver.getSolverCapability(self._solver)

    def __str__(self):
        return self.asStr()

    def _build(self):
        if self._data is not None:
            return

        mid = self._db.getValue(f'.//region[name="{self._rname}"]/material')
        phase = self._db.getValue(f'.//materials/material[@mid="{mid}"]/phase')

        if phase == 'solid':
            self._buildSolid()
        else:  # fluid
            if self._solver == 'TSLAeroFoam':
                pass
            else:
                self._buildFluid()

    def _buildSolid(self):
        self._data = {
            'ddtSchemes': {
                'default': 'steadyState'
            },
            'gradSchemes': {
                'default': 'Gauss linear'
            },
            'divSchemes': {
                'default': 'Gauss linear'
            },
            'laplacianSchemes': {
                'default': 'Gauss linear NEXT::corrected'
            },
            'interpolationSchemes': {
                'default': 'linear'
            },
            'snGradSchemes': {
                'default': 'NEXT::corrected'
            }
        }

    def _buildFluid(self):
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
            if volumeFraction == 'firstOrder':
                divSchemes.update({
                    'div(phi,alpha)': f'{bounded}Gauss Upwind',
                    'div(phirb,alpha)': f'{bounded}Gauss Upwind'
                })
            elif volumeFraction == 'secondOrder':
                divSchemes.update({
                    'div(phi,alpha)': f'{bounded}Gauss vanLeer',
                    'div(phirb,alpha)': f'{bounded}Gauss linear'
                })

        return divSchemes

    def _constructLaplacianSchemes(self):
        relaxationDisabled = self._db.getAttribute('.//numericalConditions/highOrderTermRelaxation', 'disabled')
        relFactor = self._db.getValue('.//numericalConditions/highOrderTermRelaxation/relaxationFactor')

        laplacianSchemes = {}

        if relaxationDisabled == 'true':
            laplacianSchemes['default'] = 'Gauss linear corrected'
        else:
            laplacianSchemes['default'] = f'Gauss linear limited corrected {relFactor}'

        return laplacianSchemes

    def asDict(self):
        self._build()
        return self._data

    def asStr(self):
        HEADER = {
            'version': '2.0',
            'format': 'ascii',
            'class': 'dictionary',
            'location': f'system/{self._rname}',
            'object': 'fvSchemes'
        }
        self._build()
        return str(FoamFileGenerator(self._data, header=HEADER))
