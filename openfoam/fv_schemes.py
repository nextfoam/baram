#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

import pandas as pd
from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from coredb import coredb
from resources import resource


class FvSchemes(object):
    def __init__(self, rname: str, solver: str):
        self._rname = rname
        self._solver = solver
        self._data = None

        df = pd.read_csv(resource.file('openfoam/fv_schemes.csv'), header=0, index_col=0)
        df.where(pd.notnull(df), None, inplace=True)
        self._schemes = df.applymap(lambda s: json.loads(s.replace("'", '"')), na_action='ignore').to_dict()

        df = pd.read_csv(resource.file('openfoam/fv_schemes_turbulence.csv'), header=0, index_col=0)
        df.where(pd.notnull(df), None, inplace=True)
        self._schemesTurbulence = df.applymap(lambda s: json.loads(s.replace("'", '"')), na_action='ignore').to_dict()

    def __str__(self):
        return self.asStr()

    def _build(self):
        if self._data is not None:
            return

        db = coredb.CoreDB()

        mid = db.getValue(f'.//region[name="{self._rname}"]/material')
        phase = db.getValue(f'.//materials/material[@mid="{mid}"]/phase')

        if phase == 'solid':
            self._buildSolid(db)
        else:
            self._buildFluid(db)

    def _buildSolid(self, db):
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

    def _buildFluid(self, db):
        try:
            scheme = self._schemes[self._solver]
        except KeyError:
            raise NotImplementedError

        schemeTurbulence = None
        turbulenceModel = db.getValue('.//turbulenceModels/model')
        if turbulenceModel == 'spalartAllmaras':
            schemeTurbulence = self._schemesTurbulence['spalartAllmaras']
        elif turbulenceModel == 'k-epsilon':
            model = db.getValue('.//turbulenceModels/k-epsilon/model')
            if model == 'standard':
                schemeTurbulence = self._schemesTurbulence['kEpsilon']
            elif model == 'rng':
                schemeTurbulence = self._schemesTurbulence['kEpsilon']
            elif model == 'realizable':
                schemeTurbulence = self._schemesTurbulence['realizableKE']
        elif turbulenceModel == 'k-omega':
            model = db.getValue('.//turbulenceModels/k-omega/model')
            if model == 'SST':
                schemeTurbulence = self._schemesTurbulence['kOmegaSST']

        self._data = {
            'ddtSchemes': self._constructDdtSchemes(db, scheme, schemeTurbulence),
            'gradSchemes': self._constructGradSchemes(db, scheme, schemeTurbulence),
            'divSchemes': self._constructDivSchemes(db, scheme, schemeTurbulence),
            'laplacianSchemes': scheme['laplacianNormal'],
            'interpolationSchemes': scheme['interpolation'],
            'snGradSchemes': scheme['snGrad'],
            'wallDist': scheme['wallDist']
        }

    def _constructDdtSchemes(self, db, scheme, schemeTurbulence):
        timeTransient = db.getValue('.//general/timeTransient')
        time = db.getValue('.//discretizationSchemes/time')

        ddtSchemes = {}

        if timeTransient == 'true':
            if time == 'firstOrderImplicit':
                ddtSchemes.update(scheme['ddtFirstOrder'])
            elif time == 'secondOrderImplicit':
                ddtSchemes.update(scheme['ddtSecondOrder'])
        else:
            ddtSchemes.update(scheme['ddtSteady'])

        return ddtSchemes

    def _constructGradSchemes(self, db, scheme, schemeTurbulence):
        gradSchemes = scheme['grad']

        if schemeTurbulence is not None:
            gradSchemes.update(schemeTurbulence['grad'])

        return gradSchemes

    def _constructDivSchemes(self, db, scheme, schemeTurbulence):
        timeTransient = db.getValue('.//general/timeTransient')

        energyModel     = db.getValue('.//models/energyModels')
        multiphaseModel = db.getValue('.//models/multiphaseModels/model')
        speciesModel    = db.getValue('.//models/speciesModels')

        momentum = db.getValue('.//discretizationSchemes/momentum')
        energy   = db.getValue('.//discretizationSchemes/energy')
        turbulentKineticEnergy = db.getValue('.//discretizationSchemes/turbulentKineticEnergy')

        divSchemes = {}

        if momentum == 'firstOrderUpwind':
            divSchemes.update(scheme['divMomentumFirstOrder'])
        elif momentum == 'secondOrderUpwind':
            divSchemes.update(scheme['divMomentumSecondOrder'])

        if schemeTurbulence is not None:
            if turbulentKineticEnergy == 'firstOrderUpwind':
                if timeTransient == 'true':
                    divSchemes.update(schemeTurbulence['divTurbulenceFirstOrderTransient'])
                else:
                    divSchemes.update(schemeTurbulence['divTurbulenceFirstOrderSteady'])
            elif turbulentKineticEnergy == 'secondOrderUpwind':
                if timeTransient == 'true':
                    divSchemes.update(schemeTurbulence['divTurbulenceSecondOrderTransient'])
                else:
                    divSchemes.update(schemeTurbulence['divTurbulenceSecondOrderSteady'])

        if energyModel != 'off':
            if energy == 'firstOrderUpwind':
                divSchemes.update(scheme['divEnergyFirstOrder'])
            elif energy == 'secondOrderUpwind':
                divSchemes.update(scheme['divEnergySecondOrder'])

        # ToDo: species discretization method
        if speciesModel != 'off':
            pass

        if multiphaseModel != 'off':
            if energy == 'firstOrder':
                divSchemes.update(scheme['divAlphaFirstOrder'])
            elif energy == 'secondOrder':
                divSchemes.update(scheme['divAlphaSecondOrder'])

        return divSchemes

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
