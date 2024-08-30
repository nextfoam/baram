#!/usr/bin/env python
# -*- coding: utf-8 -*-
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import ViscositySpecification
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, KEpsilonModel, KOmegaModel, NearWallTreatment
from baramFlow.coredb.turbulence_model_db import SubgridScaleModel, LengthScaleModel, RANSModel, ShieldingFunctions
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB
from baramFlow.openfoam.file_system import FileSystem


class TurbulenceProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'turbulenceProperties')

        self._rname = rname
        self._db = CoreDBReader()
        self._model = TurbulenceModelsDB.getModel()

    def build(self):
        if self._data is not None:
            return self

        if self._model == TurbulenceModel.INVISCID or self._model == TurbulenceModel.LAMINAR:
            self._constructLaminarProperties()
        elif self._model == TurbulenceModel.SPALART_ALLMARAS:
            self._constructRASproperties('SpalartAllmaras')
        elif self._model == TurbulenceModel.K_EPSILON:
            subModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/model')
            if subModel == KEpsilonModel.STANDARD.value:
                self._constructRASproperties('kEpsilon')
            elif subModel == KEpsilonModel.RNG.value:
                self._constructRASproperties('RNGkEpsilon')
            elif subModel == KEpsilonModel.REALIZABLE.value:
                treatment = self._db.getValue(
                    TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/nearWallTreatment')
                if treatment == NearWallTreatment.ENHANCED_WALL_TREATMENT.value:
                    self._constructRASproperties('realizableKEtwoLayer')
                elif treatment == NearWallTreatment.STANDARD_WALL_FUNCTIONS.value:
                    self._constructRASproperties('realizableKE')
                else:
                    raise RuntimeError
        elif self._model == TurbulenceModel.K_OMEGA:
            subModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-omega/model')
            if subModel == KOmegaModel.SST.value:
                self._constructRASproperties('kOmegaSST')
        elif self._model == TurbulenceModel.DES:
            self._constructDESProperties()
        elif self._model == TurbulenceModel.LES:
            self._constructLESProperties()

        return self

    def _constructLaminarProperties(self):
        self._data = {
            'simulationType': 'laminar'
        }

        xpath = MaterialDB.getXPath(RegionDB.getMaterial(self._rname))
        viscositySpecification = ViscositySpecification(self._db.getValue(xpath + '/viscosity/specification'))
        if viscositySpecification == ViscositySpecification.CROSS_POWER_LAW:
            self._data['laminar'] = {
                'model': 'generalizedNewtonian',
                'viscosityModel': 'CrossPowerLaw',
                'CrossPowerLawCoeffs': {
                    'nu0': self._db.getValue(xpath + '/viscosity/cross/zeroShearViscosity'),
                    'nuInf': self._db.getValue(xpath + '/viscosity/cross/infiniteShearViscosity'),
                    'm': self._db.getValue(xpath + '/viscosity/cross/naturalTime'),
                    'n': self._db.getValue(xpath + '/viscosity/cross/powerLawIndex'),
                    'tauStar': '0'  # tauStar method is not used if tauStar is zero. ESI version has a bug in handling tauStar compared to Foundation version
                }
            }
        elif viscositySpecification == ViscositySpecification.HERSCHEL_BULKLEY:
            self._data['laminar'] = {
                'model': 'generalizedNewtonian',
                'viscosityModel': 'HerschelBulkley',
                'HerschelBulkleyCoeffs': {
                    'nu0': self._db.getValue(xpath + '/viscosity/herschelBulkley/zeroShearViscosity'),
                    'tau0': self._db.getValue(xpath + '/viscosity/herschelBulkley/yieldStressThreshold'),
                    'k': self._db.getValue(xpath + '/viscosity/herschelBulkley/consistencyIndex'),
                    'n': self._db.getValue(xpath + '/viscosity/herschelBulkley/powerLawIndex')
                }
            }
        elif viscositySpecification == ViscositySpecification.BIRD_CARREAU:
            self._data['laminar'] = {
                'model': 'generalizedNewtonian',
                'viscosityModel': 'BirdCarreau',
                'BirdCarreauCoeffs': {
                    'nu0': self._db.getValue(xpath + '/viscosity/carreau/zeroShearViscosity'),
                    'nuInf': self._db.getValue(xpath + '/viscosity/carreau/infiniteShearViscosity'),
                    'k': self._db.getValue(xpath + '/viscosity/carreau/relaxationTime'),
                    'n': self._db.getValue(xpath + '/viscosity/carreau/powerLawIndex'),
                    'a': self._db.getValue(xpath + '/viscosity/carreau/linearityDeviation')
                }
            }
        elif viscositySpecification == ViscositySpecification.POWER_LAW:
            self._data['laminar'] = {
                'model': 'generalizedNewtonian',
                'viscosityModel': 'powerLaw',
                'powerLawCoeffs': {
                    'nuMax': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/maximumViscosity'),
                    'nuMin': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/minimumViscosity'),
                    'k': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/consistencyIndex'),
                    'n': self._db.getValue(xpath + '/viscosity/nonNewtonianPowerLaw/powerLawIndex')
                }
            }

    def _constructRASproperties(self, subModel):
        self._data = {
            'simulationType': 'RAS',
            'RAS': {
                'RASModel': subModel,
                'turbulence': 'on',
                'printCoeffs': 'on',
                'viscosityRatioMax': self._getMaxViscosityRatio()
            }
        }

        hasABLInlet = False
        boundaries = self._db.getBoundaryConditions(self._rname)
        for _, _, type_ in boundaries:
            if type_ == 'ablInlet':
                hasABLInlet = True
                break

        if self._model == TurbulenceModel.K_EPSILON:
            data = {
                'Prt': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/energyPrandtlNumber'),
                'Sct': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/turbulentSchmidtNumber')
            }

            if hasABLInlet:
                data.update({
                    'Cmu': 0.09,
                    'C1': 1.44,
                    'C2': 1.92,
                    'sigmaEps': 1.11
                })

            self._data['RAS']['kEpsilonCoeffs'] = data

        if subModel == 'realizableKEtwoLayer':
            self._data['RAS']['ReyStar'] = self._db.getValue(
                TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/threshold')
            self._data['RAS']['deltaRey'] = self._db.getValue(
                TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/k-epsilon/realizable/blendingWidth')

    def _constructDESProperties(self):
        ransModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/RANSModel')
        lengthScaleModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/lengthScaleModel')

        if self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/DESOptions/delayedDES') == 'true':
            shieldingFunctions = self._db.getValue(
                TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/shieldingFunctions')
            if shieldingFunctions == ShieldingFunctions.IDDES.value:
                lengthScaleModel = 'IDDESDelta'
        else:
            shieldingFunctions = 'DES'

        self._data = {
            'simulationType': 'LES',
            'LES': {
                'turbulence': 'on',
                'delta': lengthScaleModel,
                'viscosityRatioMax': self._getMaxViscosityRatio()
            },
        }

        LESModel = None
        if ransModel == RANSModel.SPALART_ALLMARAS.value:
            LESModel = 'SpalartAllmaras' + shieldingFunctions
            self._data['LES'][LESModel + 'Coeffs'] = {
                'CDES': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/modelConstants/DES'),
                'lowReCorrection':
                    ('yes'
                     if self._db.getBool(
                        TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/spalartAllmarasOptions/lowReDamping')
                     else 'no'),
                'Sct': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/turbulentSchmidtNumber')
            }
        elif ransModel == RANSModel.K_OMEGA_SST.value:
            LESModel = 'kOmegaSST' + shieldingFunctions
            self._data['LES'][LESModel] = {
                'CDESkom': self._db.getValue(
                    TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/modelConstants/DESKOmega'),
                'CDESkeps': self._db.getValue(
                    TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/des/modelConstants/DESKEpsilon'),
                'Sct': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/turbulentSchmidtNumber')
            }

        self._data['LES']['LESModel'] = LESModel

        if lengthScaleModel == 'IDDESDelta':
            self._data['LES']['IDDESDeltaCoeffs'] = {
                'hmax': 'maxDeltaxyzCubeRoot',
                'maxDeltaxyzCubeRootCoeffs': {}
            }
        elif lengthScaleModel == LengthScaleModel.VAN_DRIEST.value:
            self._data['LES']['vanDriestCoeffs'] = {
                'delta': 'cubeRootVol',
                'cubeRootVolCoeffs': {
                    'deltaCoeff': 2.0,
                },
                'kappa': 0.41,
                'Aplus': 26,
                'Cdelta': 0.158,
                'calcInterval': 1
            }
        elif lengthScaleModel == LengthScaleModel.CUBE_ROOT_VOLUME.value:
            self._data['LES']['cubeRootVolCoeffs'] = {
                'deltaCoeff': 1
            }
        elif lengthScaleModel == LengthScaleModel.SMOOTH.value:
            self._data['LES']['smoothCoeffs'] = {
                'delta': 'cubeRootVol',
                'cubeRootVolCoeffs': {
                    'deltaCoeff': 1,
                },
                'maxDeltaRatio': 1.1
            }

    def _constructLESProperties(self):
        subgridScaleModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/subgridScaleModel')
        lengthScaleModel = self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/lengthScaleModel')

        self._data = {
            'simulationType': 'LES',
            'LES': {
                'LESModel': subgridScaleModel,
                'turbulence': 'on',
                'printCoeffs': 'off',
                'delta': lengthScaleModel,
                'viscosityRatioMax': self._getMaxViscosityRatio()
            }
        }

        if subgridScaleModel == SubgridScaleModel.SMAGORINSKY.value:
            self._data['LES']['SmagorinskyCoeffs'] = {
                'Ck': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/modelConstants/k'),
                'Ce': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/modelConstants/e'),
                'Sct': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/turbulentSchmidtNumber')
            }
        elif subgridScaleModel == SubgridScaleModel.WALE.value:
            self._data['LES']['WALECoeffs'] = {
                'Ck': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/modelConstants/k'),
                'Ce': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/modelConstants/e'),
                'Cw': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/modelConstants/w'),
                'Sct': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/turbulentSchmidtNumber')
            }
        elif subgridScaleModel == SubgridScaleModel.KEQN.value:
            self._data['LES']['kEqnCoeffs'] = {
                'Ck': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/modelConstants/k'),
                'Ce': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/les/modelConstants/e'),
                'Sct': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/turbulentSchmidtNumber')
            }
        elif subgridScaleModel == SubgridScaleModel.DYNAMIC_KEQN.value:
            self._data['LES']['dynamicKEqnCoeffs'] = {
                'filter': 'simple',
                'Sct': self._db.getValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/turbulentSchmidtNumber')
            }

        if lengthScaleModel == LengthScaleModel.VAN_DRIEST.value:
            self._data['LES']['vanDriestCoeffs'] = {
                'delta': 'cubeRootVol',
                'cubeRootVolCoeffs': {
                    'deltaCoeff': 2.0,
                },
                'kappa': 0.41,
                'Aplus': 26,
                'Cdelta': 0.158,
                'calcInterval': 1
            }
        elif lengthScaleModel == LengthScaleModel.CUBE_ROOT_VOLUME.value:
            self._data['LES']['cubeRootVolCoeffs'] = {
                'deltaCoeff': 1
            }
        elif lengthScaleModel == LengthScaleModel.SMOOTH.value:
            self._data['LES']['smoothCoeffs'] = {
                'delta': 'cubeRootVol',
                'cubeRootVolCoeffs': {
                    'deltaCoeff': 1,
                },
                'maxDeltaRatio': 1.1
            }

    def _getMaxViscosityRatio(self):
        return self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/limits/maximumViscosityRatio')
