#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB, MaterialType, Specification
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.openfoam.file_system import FileSystem


EQUATION_OF_STATES = {
    Specification.CONSTANT.value                    : 'rhoConst',
    Specification.PERFECT_GAS.value                 : 'perfectGas',
    Specification.POLYNOMIAL.value                  : 'icoPolynomial',
    Specification.INCOMPRESSIBLE_PERFECT_GAS.value  : 'incompressiblePerfectGas',
    Specification.REAL_GAS_PENG_ROBINSON.value      : 'PengRobinsonGas'
}


def _constructFluid(region: str):
    db = CoreDBReader()
    mid = RegionDB.getMaterial(region)
    materialType = MaterialDB.getType(mid)
    path = MaterialDB.getXPath(mid)

    tModel = ModelsDB.getTurbulenceModel()
    viscositySpec = db.getValue(path + '/viscosity/specification')
    specificHeatSpec = db.getValue(path + '/specificHeat/specification')
    densitySpec = db.getValue(path + '/density/specification')

    transport = 'const' if tModel == TurbulenceModel.INVISCID or viscositySpec == 'constant' else viscositySpec

    thermo = {
        'type': 'heRhoThermo',
        'mixture': 'pureMixture',
        'transport': transport,
        'thermo': 'hConst' if specificHeatSpec == 'constant' else 'hPolynomial',
        'equationOfState': EQUATION_OF_STATES[densitySpec],
        'specie': 'specie',
        'energy': 'sensibleEnthalpy'
    }

    if GeneralDB.isCompressible():
        thermo['type'] = 'hePsiThermo'

    speciesModel = db.getValue('.//models/speciesModels')
    if speciesModel == 'on':
        thermo['mixture'] = 'multiComponentMixture'

    if materialType == MaterialType.MIXTURE:
        data = {
            'thermoType': thermo,
            'species': [],
            'inertSpecie': MaterialDB.getName(db.getValue(path + '/mixture/primarySpecie'))
        }

        for specie, name in MaterialDB.getSpecies(mid).items():
            spath = MaterialDB.getXPath(specie)

            data['species'].append(name)
            data[name] = {
                'thermodynamics': _mixtureThermodynamics(specificHeatSpec, db, spath),
                'transport': _mixtureTransport(tModel, transport, db, spath),
                'specie': _mixtureSpecie(db, spath)
            }
            if eos := _mixtureEquationOfState(densitySpec, db, spath):
                data[name]['equationOfState'] = eos
            data[name]['transport']['Dm'] = db.getValue(path + '/mixture/massDiffusivity')

        return data
    elif materialType == MaterialType.NONMIXTURE:
        mix = {
            'thermodynamics': _mixtureThermodynamics(specificHeatSpec, db, path),
            'transport': _mixtureTransport(tModel, transport, db, path),
            'specie': _mixtureSpecie(db, path)
        }
        if eos := _mixtureEquationOfState(densitySpec, db, path):
            mix['equationOfState'] = eos

        return {
            'thermoType': thermo,
            'mixture': {key: value for key, value in mix.items() if value}
        }
    else:
        raise AssertionError


def _mixtureEquationOfState(spec, db, path):
    data = None

    if spec == 'constant':
        rho = db.getValue(path + '/density/constant')
        data = {
            'rho': rho
        }
    elif spec == 'polynomial':
        rhoCoeffs: list[float] = [0] * 8  # To make sure that rhoCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/density/polynomial').split()):
            rhoCoeffs[i] = float(n)
        data = {
            'rhoCoeffs<8>': rhoCoeffs
        }
    elif spec == 'incompressiblePerfectGas':
        referencePressure = float(db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'))
        operatingPressure = float(db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
        data = {
            'pRef': referencePressure + operatingPressure
        }
    elif spec == 'perfectGas':
        data = None

    return data


def _mixtureThermodynamics(spec, db, path):
    data = None

    if spec == 'constant':
        cp = db.getValue(path + '/specificHeat/constant')
        data = {
            'Cp': cp,
            'Hf': 0
        }

        if GeneralDB.isDensityBased():
            data['Tref'] = 0
    elif spec == 'polynomial':
        cpCoeffs: list[float] = [0] * 8  # To make sure that cpCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/specificHeat/polynomial').split()):
            cpCoeffs[i] = float(n)
        data = {
            'Hf': 0,
            'Sf': 0,
            'CpCoeffs<8>': cpCoeffs
        }

    return data


def _mixtureTransport(tModel, transport, db, path):
    spec = db.getValue(path + '/thermalConductivity/specification')
    if spec == 'constant':
        kk = db.getValue(path + '/thermalConductivity/constant')
    elif spec == 'polynomial':
        kkCoeffs: list[float] = [0] * 8  # To make sure that kkCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/thermalConductivity/polynomial').split()):
            kkCoeffs[i] = float(n)

    data = None

    if transport == 'const':
        if tModel == TurbulenceModel.INVISCID:
            mu = 0.0
        else:
            mu = float(db.getValue(path + '/viscosity/constant'))

        if mu == 0.0:
            pr = 0.7
        else:
            cp = db.getValue(path + '/specificHeat/constant')
            pr = float(cp) * mu / float(kk)  # If viscosity spec is constant, thermalConductivity spec should be constant too

        data = {
            'mu': str(mu),
            'Pr': str(pr)
        }
    elif transport == 'polynomial':
        muCoeffs: list[float] = [0] * 8  # To make sure that muCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/viscosity/polynomial').split()):
            muCoeffs[i] = float(n)
        data = {
            'muCoeffs<8>': muCoeffs,
            'kappaCoeffs<8>': kkCoeffs  # If viscosity spec is polynomial, thermalConductivity spec should be polynomial too
        }
    elif transport == 'sutherland':
        as_ = db.getValue(path + '/viscosity/sutherland/coefficient')
        ts  = db.getValue(path + '/viscosity/sutherland/temperature')
        data = {
            'As': as_,
            'Ts': ts
        }

    return data


def _mixtureSpecie(db, path):
    mw = db.getValue(path + '/molecularWeight')
    return {
        'nMoles': 1,
        'molWeight': mw,
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

        energyModelOn = ModelsDB.isEnergyModelOn()
        self._data.update({
            'includeViscousDissipation': (
                'true'
                if db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/energy/includeViscousDissipationTerms')
                   and energyModelOn
                else 'false'),
            'includeKineticEnergy': (
                'true'
                if db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced//equations/energy/includeKineticEnergyTerms')
                   and energyModelOn
                else 'false'),
            'includePressureWork': (
                'true'
                if db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced//equations/energy/includePressureWorkTerms')
                   and energyModelOn
                else 'false')
        })

        return self
