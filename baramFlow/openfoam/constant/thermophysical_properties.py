#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb import coredb
from baramFlow.openfoam.file_system import FileSystem


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
    mid = db.retrieveValue(f'.//region[name="{region}"]/material')
    path = f'.//materials/material[@mid="{mid}"]'

    flowType = db.retrieveValue('.//general/flowType')
    if flowType == 'compressible':
        thermo['type'] = 'hePsiThermo'

    speciesModel = db.retrieveValue('.//models/speciesModels')
    if speciesModel == 'on':
        thermo['mixture'] = 'multiComponentMixture'

    spec = db.retrieveValue(path + '/density/specification')
    if spec == 'constant':
        rho = db.retrieveValue(path + '/density/constant')
        thermo['equationOfState'] = 'rhoConst'
        mix['equationOfState'] = {
            'rho': rho
        }
    elif spec == 'polynomial':
        rhoCoeffs: list[float] = [0] * 8  # To make sure that rhoCoeffs has length of 8
        for i, n in enumerate(db.retrieveValue(path + '/density/polynomial').split()):
            rhoCoeffs[i] = float(n)
        thermo['equationOfState'] = 'icoPolynomial'
        mix['equationOfState'] = {
            'rhoCoeffs<8>': rhoCoeffs
        }

    spec = db.retrieveValue(path + '/specificHeat/specification')
    if spec == 'constant':
        cp = db.retrieveValue(path + '/specificHeat/constant')
        thermo['thermo'] = 'hConst'
        mix['thermodynamics'] = {
            'Cp': cp,
            'Hf': 0
        }
    elif spec == 'polynomial':
        cpCoeffs: list[float] = [0] * 8  # To make sure that cpCoeffs has length of 8
        for i, n in enumerate(db.retrieveValue(path + '/specificHeat/polynomial').split()):
            cpCoeffs[i] = float(n)
        thermo['thermo'] = 'hPolynomial'
        mix['thermodynamics'] = {
            'Hf': 0,
            'Sf': 0,
            'CpCoeffs<8>': cpCoeffs
        }

    spec = db.retrieveValue(path + '/thermalConductivity/specification')
    if spec == 'constant':
        kk = db.retrieveValue(path + '/thermalConductivity/constant')
    elif spec == 'polynomial':
        kkCoeffs: list[float] = [0] * 8  # To make sure that kkCoeffs has length of 8
        for i, n in enumerate(db.retrieveValue(path + '/thermalConductivity/polynomial').split()):
            kkCoeffs[i] = float(n)

    tModel = db.retrieveValue('.//turbulenceModels/model')
    spec = db.retrieveValue(path + '/viscosity/specification')
    if tModel == 'inviscid' or spec == 'constant':
        if tModel == 'inviscid':
            mu = 0.0
        else:
            mu = float(db.retrieveValue(path + '/viscosity/constant'))

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
        muCoeffs: list[float] = [0] * 8  # To make sure that muCoeffs has length of 8
        for i, n in enumerate(db.retrieveValue(path + '/viscosity/polynomial').split()):
            muCoeffs[i] = float(n)
        thermo['transport'] = 'polynomial'
        mix['transport'] = {
            'muCoeffs<8>': muCoeffs,
            'kappaCoeffs<8>': kkCoeffs  # If viscosity spec is polynomial, thermalConductivity spec should be polynomial too
        }
    elif spec == 'sutherland':
        as_ = db.retrieveValue(path + '/viscosity/sutherland/coefficient')
        ts  = db.retrieveValue(path + '/viscosity/sutherland/temperature')
        thermo['transport'] = 'sutherland'
        mix['transport'] = {
            'As': as_,
            'Ts': ts
        }

    mw = db.retrieveValue(path + '/molecularWeight')
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
        'equationOfState': 'rhoConst',
        'specie': 'specie',
        'energy': 'sensibleEnthalpy'
    }

    mix = {}

    db = coredb.CoreDB()
    mid = db.retrieveValue(f'.//region[name="{region}"]/material')
    path = f'.//materials/material[@mid="{mid}"]'

    mix['specie'] = {  # This value is not used for solid. The values are fake.
        'nMoles': 1,
        'molWeight': 100
    }

    spec = db.retrieveValue(path + '/specificHeat/specification')
    if spec == 'constant':
        cp = db.retrieveValue(path + '/specificHeat/constant')
        mix['thermodynamics'] = {
            'Cp': cp,
            'Hf': 0,
            'Sf': 0
        }

    spec = db.retrieveValue(path + '/thermalConductivity/specification')
    if spec == 'constant':
        kk = db.retrieveValue(path + '/thermalConductivity/constant')
        mix['transport'] = {
            'kappa': kk,
        }

    spec = db.retrieveValue(path + '/density/specification')
    if spec == 'constant':
        rho = db.retrieveValue(path + '/density/constant')
        mix['equationOfState'] = {
            'rho': rho
        }

    return {
        'thermoType': thermo,
        'mixture': mix
    }


class ThermophysicalProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'thermophysicalProperties')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()

        mid = db.retrieveValue(f'.//region[name="{self._rname}"]/material')
        phase = db.retrieveValue(f'.//materials/material[@mid="{mid}"]/phase')

        if phase == 'solid':
            self._data = _constructSolid(self._rname)
        else:
            self._data = _constructFluid(self._rname)

        return self
