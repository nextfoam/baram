#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
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

    db = CoreDBReader()
    mid = db.getValue(f'.//region[name="{region}"]/material')
    path = f'.//materials/material[@mid="{mid}"]'

    if GeneralDB.isCompressible():
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
    elif spec == 'polynomial':
        rhoCoeffs: list[float] = [0] * 8  # To make sure that rhoCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/density/polynomial').split()):
            rhoCoeffs[i] = float(n)
        thermo['equationOfState'] = 'icoPolynomial'
        mix['equationOfState'] = {
            'rhoCoeffs<8>': rhoCoeffs
        }

    spec = db.getValue(path + '/specificHeat/specification')
    if spec == 'constant':
        cp = db.getValue(path + '/specificHeat/constant')
        thermo['thermo'] = 'hConst'
        mix['thermodynamics'] = {
            'Cp': cp,
            'Hf': 0
        }

        if GeneralDB.isDensityBased():
            mix['thermodynamics']['Tref'] = 0
    elif spec == 'polynomial':
        cpCoeffs: list[float] = [0] * 8  # To make sure that cpCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/specificHeat/polynomial').split()):
            cpCoeffs[i] = float(n)
        thermo['thermo'] = 'hPolynomial'
        mix['thermodynamics'] = {
            'Hf': 0,
            'Sf': 0,
            'CpCoeffs<8>': cpCoeffs
        }

    spec = db.getValue(path + '/thermalConductivity/specification')
    if spec == 'constant':
        kk = db.getValue(path + '/thermalConductivity/constant')
    elif spec == 'polynomial':
        kkCoeffs: list[float] = [0] * 8  # To make sure that kkCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/thermalConductivity/polynomial').split()):
            kkCoeffs[i] = float(n)

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
        muCoeffs: list[float] = [0] * 8  # To make sure that muCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/viscosity/polynomial').split()):
            muCoeffs[i] = float(n)
        thermo['transport'] = 'polynomial'
        mix['transport'] = {
            'muCoeffs<8>': muCoeffs,
            'kappaCoeffs<8>': kkCoeffs  # If viscosity spec is polynomial, thermalConductivity spec should be polynomial too
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
        'molWeight': mw,
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

    db = CoreDBReader()
    mid = db.getValue(f'.//region[name="{region}"]/material')
    path = f'.//materials/material[@mid="{mid}"]'

    mix['specie'] = {  # This value is not used for solid. The values are fake.
        'nMoles': 1,
        'molWeight': 100
    }

    spec = db.getValue(path + '/specificHeat/specification')
    if spec == 'constant':
        cp = db.getValue(path + '/specificHeat/constant')
        mix['thermodynamics'] = {
            'Cp': cp,
            'Hf': 0,
            'Sf': 0
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
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'thermophysicalProperties')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = CoreDBReader()

        mid = db.getValue(f'.//region[name="{self._rname}"]/material')
        phase = db.getValue(f'.//materials/material[@mid="{mid}"]/phase')

        if phase == 'solid':
            self._data = _constructSolid(self._rname)
        else:
            self._data = _constructFluid(self._rname)

        return self
