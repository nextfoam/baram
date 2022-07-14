#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from openfoam.dictionary_file import DictionaryFile


def _constructFluid(region: str):
    thermo = {
        'type': 'heRhoThermo',
        'mixture': 'pureMixture',
        'transport': 'sutherland',
        'thermo': 'hConst',
        'equationOfState': 'perfectGas',
        'specie': 'specie',
        'energy': 'sensibleEnthalpy'
    }

    mix = dict()

    db = coredb.CoreDB()
    mid = db.getValue(f'.//region[name="{region}"]/material')
    path = f'.//materials/material[@mid="{mid}"]'

    flowType = db.getValue('.//general/flowType')
    if flowType == 'compressible':
        thermo['type'] = 'hePsiThermo'

    speciesModel = db.getValue('.//models/speciesModels')
    if speciesModel == 'on':
        thermo['mixture'] = 'multiComponentMixture'

    spec = db.getValue(path + '/density/specification')
    if spec == 'constant':
        rho = db.getValue(path + '/density/constant')
        thermo['equationOfState'] = 'rhoConst'
        mix['equationOfState'] = {
            'rho': rho
        }

    spec = db.getValue(path + '/specificHeat/specification')
    if spec == 'constant':
        cp = db.getValue(path + '/specificHeat/constant')
        thermo['thermo'] = 'hConst'
        mix['thermodynamics'] = {
            'Cp': cp,
            'Hf': 0
        }
    elif spec == 'polynomial':
        cpCoeffs = db.getValue(path + '/specificHeat/polynomial')
        thermo['thermo'] = 'polynomial'
        mix['thermodynamics'] = {
            'Hf': 0,
            'Sf': 0,
            'CpCoeffs': cpCoeffs
        }

    spec = db.getValue(path + '/thermalConductivity/specification')
    if spec == 'constant':
        kk = db.getValue(path + '/thermalConductivity/constant')
    elif spec == 'polynomial':
        kkCoeffs = db.getValue(path + '/thermalConductivity/polynomial')

    tModel = db.getValue('.//turbulenceModels/model')
    spec = db.getValue(path + '/viscosity/specification')
    if tModel == 'inviscid' or spec == 'constant':
        if tModel == 'inviscid':
            mu = 0.0
        else:
            mu = float(db.getValue(path + '/viscosity/constant'))

        if mu == 0.0:
            pr = 0.7
        else:
            pr = float(cp) * mu / float(kk)  # If viscosity spec is constant, thermalConductivity spec should be constant too

        thermo['transport'] = 'const'
        mix['transport'] = {
            'mu': str(mu),
            'Pr': str(pr)
        }
    elif spec == 'polynomial':
        muCoeffs = db.getValue(path + '/viscosity/polynomial')
        thermo['transport'] = 'polynomial'
        mix['transport'] = {
            'muCoeffs': muCoeffs,
            'kappaCoeffs': kkCoeffs  # If viscosity spec is polynomial, thermalConductivity spec should be polynomial too
        }
    elif spec == 'sutherland':
        as_ = db.getValue(path + '/viscosity/sutherland/coefficient')
        ts  = db.getValue(path + '/viscosity/sutherland/temperature')
        thermo['transport'] = 'sutherland'
        mix['transport'] = {
            'As': as_,
            'Ts': ts
        }

    mw = db.getValue(path + '/molecularWeight')
    mix['specie'] = {
        'nMoles': 1,
        'molWeight': mw
    }

    return {
        'thermoType': thermo,
        'mixture': mix
    }


def _constructSolid(region: str):
    thermo = {
        'type': 'heSolidThermo',
        'mixture': 'pureMixture',
        'transport': 'constIso',
        'thermo': 'hConst',
        'equationsOfState': 'rhoConst',
        'specie': 'specie',
        'energy': 'sensibleEnthalpy'
    }

    mix = {}

    db = coredb.CoreDB()
    mid = db.getValue(f'.//region[name="{region}"]/material')
    path = f'.//materials/material[@mid="{mid}"]'

    mw = db.getValue(path + '/molecularWeight')
    mix['specie'] = {
        'molWeight': mw
    }

    spec = db.getValue(path + '/specificHeat/specification')
    if spec == 'constant':
        cp = db.getValue(path + '/specificHeat/constant')
        mix['thermodynamics'] = {
            'Cp': cp,
            'Hf': 0
        }

    spec = db.getValue(path + '/thermalConductivity/specification')
    if spec == 'constant':
        kk = db.getValue(path + '/thermalConductivity/constant')
        mix['transport'] = {
            'kappa': kk,
        }

    spec = db.getValue(path + '/density/specification')
    if spec == 'constant':
        rho = db.getValue(path + '/density/constant')
        mix['equationOfState'] = {
            'rho': rho
        }

    return {
        'thermoType': thermo,
        'mixture': mix
    }


class ThermophysicalProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'thermophysicalProperties')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()

        mid = db.getValue(f'.//region[name="{self._rname}"]/material')
        phase = db.getValue(f'.//materials/material[@mid="{mid}"]/phase')

        if phase == 'solid':
            self._data = _constructSolid(self._rname)
        else:
            self._data = _constructFluid(self._rname)

        return self
