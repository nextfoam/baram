#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.base import Function1Scalar
from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import DPMParticleType
from baramFlow.openfoam.dictionary_helper import DictionaryHelper
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.base.material.material import UNIVERSAL_GAS_CONSTANT, MaterialType, DensitySpecification, Phase, SpecificHeatSpecification, TransportSpecification
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.openfoam.file_system import FileSystem


EQUATION_OF_STATES = {
    DensitySpecification.CONSTANT                   : 'rhoConst',
    DensitySpecification.PERFECT_GAS                : 'perfectGas',
    DensitySpecification.POLYNOMIAL                 : 'icoPolynomial',
    DensitySpecification.INCOMPRESSIBLE_PERFECT_GAS : 'incompressiblePerfectGas',
    DensitySpecification.REAL_GAS_PENG_ROBINSON     : 'PengRobinsonGas',
    DensitySpecification.BOUSSINESQ                 : 'Boussinesq',
    DensitySpecification.PERFECT_FLUID              : 'perfectFluid'
}


THERMO = {
    SpecificHeatSpecification.CONSTANT    : 'hConst',
    SpecificHeatSpecification.POLYNOMIAL  : 'hPolynomial',
    SpecificHeatSpecification.JANAF       : 'janaf',
}


TRANSPORT_FLUID = {
    TransportSpecification.CONSTANT         : 'const',
    TransportSpecification.SUTHERLAND       : 'sutherland',
    TransportSpecification.POLYNOMIAL       : 'polynomial',
    TransportSpecification.CROSS_POWER_LAW  : 'cross',
    TransportSpecification.HERSCHEL_BULKLEY : 'herschelBulkley',
    TransportSpecification.BIRD_CARREAU     : 'carreau',
    TransportSpecification.POWER_LAW        : 'nonNewtonianPowerLaw',
    TransportSpecification.TABLE            : 'tabulated',
}


TRANSPORT_SOLID = {
    TransportSpecification.CONSTANT         : 'constIso',
    TransportSpecification.POLYNOMIAL       : 'polynomial',
    TransportSpecification.TABLE            : 'tabulated',
}


def _getEnthalpyValue(mid: str):
    db = CoreDBReader()
    xpath = MaterialDB.getXPath(mid)

    h0 = float(db.getValue(xpath + '/standardStateEnthalpy'))
    T0 = float(db.getValue(xpath + '/referenceTemperature'))
    spec = SpecificHeatSpecification(db.getValue(xpath + '/specificHeat/specification'))

    if spec == SpecificHeatSpecification.CONSTANT:
        Cp = float(db.getValue(xpath + '/specificHeat/constant'))

        return ('polynomial', [
            [h0 - Cp * T0, 0],
            [Cp, 1]
        ])

    elif spec == SpecificHeatSpecification.POLYNOMIAL:
        # Integration of polynomial: ∫(a_n * T^n) dT = a_n/(n+1) * T^(n+1)
        # H(T) = h0 + ∫(T0 to T) Cp(T) dT
        #      = h0 + [a0*T + a1*T^2/2 + a2*T^3/3 + ... + a7*T^8/8]
        #          - [a0*T0 + a1*T0^2/2 + a2*T0^3/3 + ... + a7*T0^8/8]

        coeffs = [float(a) for a in db.getValue(xpath + '/specificHeat/polynomial').split()]
        b = [(a / (i + 1), i + 1) for i, a in enumerate(coeffs) if a != 0]
        b0 = h0 - sum(n * (T0 ** e) for n, e in b)

        return ('polynomial', [[b0, 0]] + [[n, e] for n, e in b])

    else:
        return ('constant', '0')


def _constructFluid(rname: str):
    db = CoreDBReader()
    mid = RegionDB.getMaterial(rname)
    materialType = MaterialDB.getType(mid)
    path = MaterialDB.getXPath(mid)

    tModel = TurbulenceModelsDB.getModel()
    transportSpec = TransportSpecification(db.getValue(path + '/transport/specification'))
    specificHeatSpec = SpecificHeatSpecification(db.getValue(path + '/specificHeat/specification'))
    densitySpec = DensitySpecification(db.getValue(path + '/density/specification'))

    thermo = {
        'type': 'heRhoThermo',
        'mixture': 'pureMixture',
        'transport': ('const' if tModel == TurbulenceModel.INVISCID
                                 or transportSpec == TransportSpecification.CONSTANT
                                 or MaterialDB.isNonNewtonianSpecification(transportSpec)
                      else TRANSPORT_FLUID[transportSpec]),
        'thermo': THERMO[specificHeatSpec],
        'equationOfState': EQUATION_OF_STATES[densitySpec],
        'specie': 'specie',
        'energy': 'sensibleEnthalpy'
    }

    if GeneralDB.isCompressible():
        thermo['type'] = 'hePsiThermo'

    if materialType == MaterialType.MIXTURE:
        thermo['mixture'] = 'multiComponentMixture'

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
                'transport': _mixtureTransport(tModel, transportSpec, db, spath),
                'specie': _mixtureSpecie(db, spath)
            }
            if eos := _mixtureEquationOfState(densitySpec, db, spath):
                data[name]['equationOfState'] = eos
            data[name]['transport']['Dm'] = db.getValue(path + '/mixture/massDiffusivity')

        return data
    elif materialType == MaterialType.NONMIXTURE:
        mix = {
            'thermodynamics': _mixtureThermodynamics(specificHeatSpec, db, path),
            'transport': _mixtureTransport(tModel, transportSpec, db, path),
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

    if spec == DensitySpecification.CONSTANT:
        rho = db.getValue(path + '/density/constant')
        data = {
            'rho': rho
        }
    elif spec == DensitySpecification.POLYNOMIAL:
        rhoCoeffs: list[float] = [0] * 8  # To make sure that rhoCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/density/polynomial').split()):
            rhoCoeffs[i] = float(n)
        data = {
            'rhoCoeffs<8>': rhoCoeffs
        }
    elif spec == DensitySpecification.INCOMPRESSIBLE_PERFECT_GAS:
        referencePressure = float(db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'))
        operatingPressure = float(db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
        data = {
            'pRef': referencePressure + operatingPressure
        }
    elif spec == DensitySpecification.PERFECT_GAS:
        data = None
    elif spec == DensitySpecification.BOUSSINESQ:
        data = {
            'rho0': db.getValue(path + '/density/boussinesq/rho0'),
            'T0': db.getValue(path + '/density/boussinesq/T0'),
            'beta': db.getValue(path + '/density/boussinesq/beta')
        }
    elif spec == DensitySpecification.PERFECT_FLUID:
        rho0 = float(db.getValue(path + '/density/perfectFluid/rho0'))
        data = {
            'rho0': rho0,
            'R': 1 / (rho0
                      * float(db.getValue(path + '/density/perfectFluid/T'))
                      * float(db.getValue(path + '/density/perfectFluid/beta')))
        }

    return data


def _mixtureThermodynamics(specificHeatSpec, db, path):
    data = None

    if specificHeatSpec == SpecificHeatSpecification.CONSTANT:
        cp = db.getValue(path + '/specificHeat/constant')
        data = {
            'Cp': cp,
            'Hf': 0
        }

        if GeneralDB.isDensityBased():
            data['Tref'] = 0
    elif specificHeatSpec == SpecificHeatSpecification.POLYNOMIAL:
        cpCoeffs: list[float] = [0] * 8  # To make sure that cpCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/specificHeat/polynomial').split()):
            cpCoeffs[i] = float(n)
        data = {
            'Hf': 0,
            'Sf': 0,
            'CpCoeffs<8>': cpCoeffs
        }
    elif specificHeatSpec == SpecificHeatSpecification.JANAF:
        data = {
            'Tlow': db.getValue(path + '/specificHeat/janaf/lowTemperature'),
            'Thigh': db.getValue(path + '/specificHeat/janaf/highTemperature'),
            'Tcommon': db.getValue(path + '/specificHeat/janaf/commonTemperature'),
            'highCpCoeffs': db.getValue(path + '/specificHeat/janaf/highCoefficients').split(),
            'lowCpCoeffs': db.getValue(path + '/specificHeat/janaf/lowCoefficients').split()
        }

    return data


def _mixtureTransport(tModel, transportSpec, db, path):
    if tModel == TurbulenceModel.INVISCID:
        mu = 0.0
        pr = 0.7

        return {
            'mu': str(mu),
            'Pr': str(pr)
        }

    if transportSpec == TransportSpecification.CONSTANT:
        mu = float(db.getValue(path + '/transport/viscosity'))
        kk = float(db.getValue(path + '/transport/thermalConductivity'))
        if mu == 0.0:
            pr = 0.7
        else:
            cp = float(db.getValue(path + '/specificHeat/constant'))
            pr = cp * mu / kk

        return {
            'mu': str(mu),
            'Pr': str(pr)
        }

    elif transportSpec == TransportSpecification.POLYNOMIAL:
        muCoeffs: list[float] = [0] * 8  # To make sure that muCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/transport/polynomial/viscosity').split()):
            muCoeffs[i] = float(n)

        kkCoeffs: list[float] = [0] * 8  # To make sure that kkCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/transport/polynomial/thermalConductivity').split()):
            kkCoeffs[i] = float(n)

        return {
            'muCoeffs<8>': muCoeffs,
            'kappaCoeffs<8>': kkCoeffs
        }

    elif transportSpec == TransportSpecification.SUTHERLAND:
        as_ = db.getValue(path + '/transport/sutherland/coefficient')
        ts  = db.getValue(path + '/transport/sutherland/temperature')

        return {
            'As': as_,
            'Ts': ts
        }

    rho = float(db.getValue(path + '/density/constant'))

    if transportSpec == TransportSpecification.CROSS_POWER_LAW:
        return {
            'mu': rho * float(db.getValue(path + '/transport/cross/zeroShearViscosity')),
            'Pr': 0.7
        }

    if transportSpec == TransportSpecification.HERSCHEL_BULKLEY:
        return {
            'mu': rho * float(db.getValue(path + '/transport/herschelBulkley/zeroShearViscosity')),
            'Pr': 0.7
        }

    if transportSpec == TransportSpecification.BIRD_CARREAU:
        return {
            'mu': rho * float(db.getValue(path + '/transport/carreau/zeroShearViscosity')),
            'Pr': 0.7
        }

    if transportSpec == TransportSpecification.POWER_LAW:
        return {
            'mu': rho * float(db.getValue(path + '/transport/nonNewtonianPowerLaw/consistencyIndex')),
            'Pr': 0.7
        }


def _mixtureSpecie(db, path):
    mw = db.getValue(path + '/molecularWeight')
    return {
        'nMoles': 1,
        'molWeight': mw,
    }


def _constructSolid(rname: str):
    db = CoreDBReader()
    mid = db.getValue(f'/regions/region[name="{rname}"]/material')
    path = f'/materials/material[@mid="{mid}"]'

    transportSpec = TransportSpecification(db.getValue(path + '/transport/specification'))
    specificHeatSpec = SpecificHeatSpecification(db.getValue(path + '/specificHeat/specification'))
    densitySpec = DensitySpecification(db.getValue(path + '/density/specification'))

    thermo = {
        'type': 'heSolidThermo',
        'mixture': 'pureMixture',
        'transport': TRANSPORT_SOLID[transportSpec],
        'thermo': THERMO[specificHeatSpec],
        'equationOfState': EQUATION_OF_STATES[densitySpec],
        'specie': 'specie',
        'energy': 'sensibleEnthalpy'
    }

    mix = {}
    mix['specie'] = {  # This value is not used for solid. The values are fake.
        'nMoles': 1,
        'molWeight': 100
    }

    if specificHeatSpec == SpecificHeatSpecification.CONSTANT:
        cp = db.getValue(path + '/specificHeat/constant')
        mix['thermodynamics'] = {
            'Cp': cp,
            'Hf': 0,
            'Sf': 0
        }

    elif specificHeatSpec == SpecificHeatSpecification.POLYNOMIAL:
        cpCoeffs: list[float] = [0] * 8  # To make sure that cpCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/specificHeat/polynomial').split()):
            cpCoeffs[i] = float(n)

        mix['thermodynamics'] = {
            'Hf': 0,
            'Sf': 0,
            'CpCoeffs<8>': cpCoeffs
        }

    if transportSpec == TransportSpecification.CONSTANT:
        kk = db.getValue(path + '/transport/thermalConductivity')
        mix['transport'] = {
            'kappa': kk,
        }

    elif transportSpec == TransportSpecification.POLYNOMIAL:
        thermo['transport'] = 'polynomial'

        kkCoeffs: list[float] = [0] * 8  # To make sure that kkCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/transport/polynomial/thermalConductivity').split()):
            kkCoeffs[i] = float(n)

        mix['transport'] = {
            'kappaCoeffs<8>': kkCoeffs
        }

    if densitySpec == DensitySpecification.CONSTANT:
        rho = db.getValue(path + '/density/constant')
        mix['equationOfState'] = {
            'rho': rho
        }

    elif densitySpec == DensitySpecification.POLYNOMIAL:
        rhoCoeffs: list[float] = [0] * 8  # To make sure that rhoCoeffs has length of 8
        for i, n in enumerate(db.getValue(path + '/density/polynomial').split()):
            rhoCoeffs[i] = float(n)

        mix['equationOfState'] = {
            'rhoCoeffs<8>': rhoCoeffs
        }

    return {
        'thermoType': thermo,
        'mixture': mix
    }


def _constructSLGThermo(rname: str) -> dict:
    db = CoreDBReader()
    dictHelper = DictionaryHelper()

    data = {
        'liquids': {},
        'solids': {},
    }

    # Region property

    mid = RegionDB.getMaterial(rname)
    if MaterialDB.getType(mid) != MaterialType.MIXTURE:  # Requirement for SLG Thermo
        return {}

    diffusivity = db.getValue(MaterialDB.getXPath(mid) + '/mixture/massDiffusivity')

    # Build species table to find a specie corresponding to liquids in the droplet
    species: dict[str, str] = {}  # {<chemicalFormula>: <specieName>}
    for specie, name in MaterialDB.getSpecies(mid).items():
        chemicalFormula = str(db.getValue(MaterialDB.getXPath(specie) + '/chemicalFormula'))
        species[chemicalFormula] = name

    for mid in DPMModelManager.dropletCompositionMaterials():
        phase = MaterialDB.getPhase(mid)
        xpath = MaterialDB.getXPath(mid)

        if phase == Phase.LIQUID:
            chemicalFormula = db.getValue(xpath + '/chemicalFormula')
            if chemicalFormula not in species:  # It should be in the fluid mixture
                continue

            name = species[chemicalFormula]  # use the name of corresponding specie in the fluid

            rho = db.getValue(xpath + '/density/constant')       # support only constant spec for now
            cp  = db.getValue(xpath + '/specificHeat/constant')  # support only constant spec for now
            mu  = db.getValue(xpath + '/transport/viscosity')    # support only constant spec for now
            kappa = db.getValue(xpath + '/transport/thermalConductivity')  # support only constant spec for now

            molecularWeight          = db.getValue(xpath + '/molecularWeight')
            criticalTemperature      = db.getValue(xpath + '/criticalTemperature')
            criticalPressure         = db.getValue(xpath + '/criticalPressure')
            criticalSpecificVolume   = db.getValue(xpath + '/criticalSpecificVolume')
            tripleTemperature        = db.getValue(xpath + '/tripleTemperature')
            triplePressure           = db.getValue(xpath + '/triplePressure')
            normalBoilingTemperature = db.getValue(xpath + '/normalBoilingTemperature')
            acentricFactor           = db.getValue(xpath + '/acentricFactor')
            saturationPressure      = Function1Scalar.fromElement(db.getElement(xpath + '/saturationPressure'))
            enthalpyOfVaporization  = Function1Scalar.fromElement(db.getElement(xpath + '/enthalpyOfVaporization'))
            dropletSurfaceTension   = Function1Scalar.fromElement(db.getElement(xpath + '/dropletSurfaceTension'))

            Zc = float(criticalPressure) * float(criticalSpecificVolume) / (UNIVERSAL_GAS_CONSTANT * float(criticalTemperature))

            data['liquids'][name] = {
                'type': 'liquid',
                'W': molecularWeight,
                'Tc': criticalTemperature,
                'Pc': criticalPressure,
                'Vc': criticalSpecificVolume,
                'Zc': Zc,
                'Tt': tripleTemperature,
                'Pt': triplePressure,
                'Tb': normalBoilingTemperature,
                'dipm':  0,   # Not used for now
                'omega': acentricFactor,
                'delta': 0,  # Not used for now
                'rho': ('constant', rho),
                'pv': dictHelper.function1ScalarValue(saturationPressure),
                'hl': dictHelper.function1ScalarValue(enthalpyOfVaporization),
                'Cp': ('constant', cp),
                'h': _getEnthalpyValue(mid),
                'Cpg': ('constant', 0),  # Not used in the Sover
                'B': ('constant', 0),   # Not used in the Sover
                'mu': ('constant', mu),
                'mug': ('constant', 0),  # Not used in the Sover
                'kappa': ('constant', kappa),
                'kappag': ('constant', 0),  # Not used in the Sover
                'sigma': dictHelper.function1ScalarValue(dropletSurfaceTension),
                'D': ('constant', diffusivity),
            }

        elif phase == Phase.SOLID:  # SOLID supports only constant spec
            name = db.getValue(xpath + '/name')

            rho   = db.getValue(xpath + '/density/constant')
            cp    = db.getValue(xpath + '/specificHeat/constant')
            kappa = db.getValue(xpath + '/transport/thermalConductivity')
            molecularWeight = db.getValue(xpath + '/molecularWeight')
            emissivity      = db.getValue(xpath + '/emissivity')

            data['solids'][name] = {
                'defaultCoeffs': 'no',
                'rho': rho,
                'Cp': cp,
                'kappa': kappa,
                'Hf': 0,  # Heat of formation, For chemical reaction. Not used for now
                'emissivity': emissivity,  # Seems not used
                'W': molecularWeight,
                'nu': 0.3,  # Poisson's ratio. Seems not used. for Soot
                'E': 7000000000,  # Young's modulus, Seems not used. 7GPa for Soot
            }

    return data


class ThermophysicalProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'thermophysicalProperties')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = CoreDBReader()

        mid = db.getValue(f'/regions/region[name="{self._rname}"]/material')
        phase = db.getValue(f'/materials/material[@mid="{mid}"]/phase')

        if phase == 'solid':
            self._data = _constructSolid(self._rname)
        else:
            self._data = _constructFluid(self._rname)
            if DPMModelManager.isModelOn():
                if DPMModelManager.particleType() == DPMParticleType.DROPLET:
                    self._data.update(_constructSLGThermo(self._rname))

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
