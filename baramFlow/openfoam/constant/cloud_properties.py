#!/usr/bin/env python
# -*- coding:, # utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile, DataClass

from baramFlow.base.boundary.boundary import BoundaryManager, WallInteractionType
from baramFlow.base.model.DPM_model import DPMModelManager, KinematicModel, FlowRate, DiameterDistribution, Injection
from baramFlow.base.model.DPM_model import ConeInjection, PointInjection, SurfaceInjection
from baramFlow.base.model.model import DPMTrackingScheme, DPMParticleType, DPMTurbulentDispersion, DPMFlowRateSpec
from baramFlow.base.model.model import DPMInjectionType, DPMDiameterDistribution
from baramFlow.base.model.model import DPMParticleVelocityType, DPMParticleSpeed, DPMLiftForce
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB, TurbulenceModel
from baramFlow.openfoam.dictionary_helper import DictionaryHelper
from baramFlow.openfoam.file_system import FileSystem


class CloudProperties(DictionaryFile):
    def __init__(self, objectName):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(), objectName)

        self._helper = DictionaryHelper()
        self._db = CoreDBReader()

    def _buildBaseCloudProperties(self, properties):
        integrationScheme = {
            DPMTrackingScheme.IMPLICIT: 'Euler',
            DPMTrackingScheme.ANALYTIC: 'analytical'
        }.get(properties.numericalConditions.trackingScheme)

        particleType = properties.particleType
        if particleType == DPMParticleType.INERT:
            mid = properties.inert.inertParticle
        else:
            mid = properties.droplet.composition[0].mid

        self._data = {
            'solution': {
                'active': 'true',
                'calcFrequency': 10,
                'maxTrackTime': 5.0,
                'coupled': self._helper.boolValue(properties.numericalConditions.interactionWithContinuousPhase),
                'transient': self._helper.boolValue(GeneralDB.isTimeTransient()),
                'cellValueSourceCorrection': self._helper.boolValue(properties.numericalConditions.nodeBasedAveraging),
                'maxCo': self._helper.pFloatValue(properties.numericalConditions.maxParticleCourantNumber),
                'sourceTerms': {
                    'resetOnStartup': 'false',
                    'schemes': {
                    }
                },
                'interpolationSchemes' : {
                    'rho': 'cell',
                    'U': 'cellPoint',
                    '"thermo.mu"':  'cell',
                    'T': 'cell',
                    'Cp':  'cell',
                    'kappa': 'cell',
                    'p':  'cell',
                    'muc':  'cell',
                },
                'integrationSchemes': {
                    'U': integrationScheme,
                    'T': integrationScheme
                }
            },
            'constantProperties': {
                'rho0': self._db.getValue(MaterialDB.getXPath(mid) + '/density/constant'),
                't0': self._helper.pFloatValue(properties.droplet.temperature)
            },
            'subModels': {
                'particleForces': self._constructParticleForce(properties.kinematicModel),
                'injectionModels': self._constructInjections(DPMModelManager.injections()),
                'patchInteractionModel': 'multiInteraction',
                'surfaceFilmModel': 'none',
                'stochasticCollisionModel': 'none',
                'multiInteractionCoeffs': self._constructMultiInteractionCoeff(),
                'phaseChangeModel' : 'none',
                'devolatilisationModel': 'none',
                'surfaceReactionModel': 'none',
            },
            'cloudFunctions': {}
        }

        turbulenceDispersion = (
            DPMTurbulentDispersion.NONE if TurbulenceModelsDB.getModel() != TurbulenceModel.SPALART_ALLMARAS
            else properties.turbulentDispersion)
        self._data['subModels']['dispersionModel'] = turbulenceDispersion.value

        return self

    def _constructParticleForce(self, model: KinematicModel):
        data = {
            model.dragForce.specification.value: ''
        }

        if model.liftForce != DPMLiftForce.NONE:
            data[model.liftForce.value] = ''

        if model.gravity:
            data['gravity'] = ''

        if model.pressureGradient:
            data['pressureGradient'] = ''

        data['nonSphereDrag'] = {
            'phi': self._helper.pFloatValue(model.dragForce.nonSphericalSettings.shapeFactor)
        }

        if not model.brownianMotionForce.disabled:
            data['BrownianMotion'] = {
                'lambda': self._helper.pFloatValue(model.brownianMotionForce.molecularFreePathLength),
                'turbulence': self._helper.boolValue(model.brownianMotionForce.useTurbulence),
                'spherical': 'false'
            }

        return data

    def _constructFlowRate(self, flowRate: FlowRate):
        startTime = self._helper.pFloatValue(flowRate.startTime)
        duration = float(self._helper.pFloatValue(flowRate.stopTime)) - float(startTime)

        if flowRate.specification == DPMFlowRateSpec.PARTICLE_COUNT:
            return {
                'parcelBasisType': 'fixed',
                'parcelsPerSecond': self._helper.pFloatValue(flowRate.particleCount.parcelPerSecond),
                'nParticle': self._helper.pFloatValue(flowRate.particleCount.numberOfParticlesPerParcel),
                'massTotal': '0',
                'flowRateProfile': self._helper.function1ScalarValue(flowRate.particleVolume.volumeFlowRate),
                'SOI': startTime,
                'duration': duration
            }
        elif flowRate.specification == DPMFlowRateSpec.PARTICLE_VOLUME:
            return {
                'parcelBasisType': 'mass',
                'parcelsPerSecond': self._helper.pFloatValue(flowRate.particleVolume.parcelPerSecond),
                'massTotal': self._helper.pFloatValue(flowRate.particleVolume.totalMass),
                'flowRateProfile': self._helper.function1ScalarValue(flowRate.particleVolume.volumeFlowRate),
                'SOI': startTime,
                'duration': duration
            }

    def _constructSizeDistribution(self, distribution: DiameterDistribution):
        if distribution.type == DPMDiameterDistribution.UNIFORM:
            return {
                'type': 'fixedValue',
                'fixedValueDistribution': {
                    'value': self._helper.pFloatValue(distribution.diameter)
                }
            }
        elif distribution.type == DPMDiameterDistribution.LINEAR:
            return {
                'type': 'uniform',
                'uniformDistribution': {
                    'minValue': self._helper.pFloatValue(distribution.minDiameter),
                    'maxValue': self._helper.pFloatValue(distribution.maxDiameter)
                }
            }
        elif distribution.type == DPMDiameterDistribution.ROSIN_RAMMLER:
            return {
                'type': 'RosinRammler',
                'RosinRammlerDistribution': {
                    'minValue': self._helper.pFloatValue(distribution.minDiameter),
                    'maxValue': self._helper.pFloatValue(distribution.maxDiameter),
                    'lambda': self._helper.pFloatValue(distribution.meanDiameter),
                    'n': self._helper.pFloatValue(distribution.spreadParameter)
                }
            }
        elif distribution.type == DPMDiameterDistribution.MASS_ROSIN_RAMMLER:
            return {
                'type': 'massRosinRammler',
                'massRosinRammlerDistribution': {
                    'minValue': self._helper.pFloatValue(distribution.minDiameter),
                    'maxValue': self._helper.pFloatValue(distribution.maxDiameter),
                    'lambda': self._helper.pFloatValue(distribution.meanDiameter),
                    'n': self._helper.pFloatValue(distribution.spreadParameter)
                }
            }
        elif distribution.type == DPMDiameterDistribution.NORMAL:
            return {
                'type': 'normal',
                'massRosinRammlerDistribution': {
                    'mu': self._helper.pFloatValue(distribution.meanDiameter),
                    'sigma': self._helper.pFloatValue(distribution.stdDeviation),
                    'minValue': self._helper.pFloatValue(distribution.minDiameter),
                    'maxValue': self._helper.pFloatValue(distribution.maxDiameter)
                }
            }

    def _constructManualInjection(self, injection: PointInjection):
        positionsFileName = 'cloudPositions'
        positionsFile = DictionaryFile(self._casePath, self._header['location'], positionsFileName, DataClass.CLASS_VECTOR_FIELD,
                                       data=[self._helper.vectorValue(v) for v in injection.positions])
        positionsFile.write()

        return {
            'type': 'manualInjection',
            'parcelBasisType': 'fixed',
            'nParticle': '1',
            'massTotal': '0',
            'parcelsPerSecond': self._helper.pFloatValue(injection.numberOfParticlesPerPoint),
            'SOI': self._helper.pFloatValue(injection.injectionTime),
            'positionsFile': f'"{positionsFileName}"',
            'U0': self._helper.vectorValue(injection.particleVelocity)
        }

    def _constructPatchInjection(self, injection: SurfaceInjection):
        return {
            'type': 'patchInjection',
            'patch': BoundaryDB.getBoundaryName(injection.bcid),
            'velocityType': ('fixedValue' if injection.particleVelocity.type == DPMParticleVelocityType.CONSTANT
                             else 'patchValue' if injection.particleVelocity.type == DPMParticleVelocityType.FACE_VALUE
                             else 'zeroGradient'),
            'U0': self._helper.vectorValue(injection.particleVelocity.value),
        }

    def _constructConeInjection(self, injection: ConeInjection):
        return {
            'type': 'coneNozzleInjection',
            'injectionMethod': injection.injectorType.value,
            'flowType': ('constantVelocity' if injection.particleSpeed == DPMParticleSpeed.FROM_INJECTION_SPEED
                         else 'pressureDrivenVelocity' if injection.particleSpeed == DPMParticleSpeed.FROM_PRESSURE
                         else 'flowRateAndDischarge'),
            'UMag': self._helper.pFloatValue(injection.injectionSpeed),
            'Pinj': self._helper.function1ScalarValue(injection.injectorPressure),
            'Cd': self._helper.function1ScalarValue(injection.dischargeCoeff),
            'outerDiameter': float(self._helper.pFloatValue(injection.outerRadius)) * 2,
            'innerDiameter': float(self._helper.pFloatValue(injection.innerRadius)) * 2,
            'thetaInner': self._helper.function1ScalarValue(injection.innerConeAngle),
            'thetaOuter': self._helper.function1ScalarValue(injection.outerConeAngle),
            'position': self._helper.function1VectorValue(injection.position),
            'direction': self._helper.function1VectorValue(injection.axis),
            'omega': self._helper.function1ScalarValue(injection.swirlVelocity),
        }

    def _constructInjections(self, injections: list[Injection]):
        data = {}

        for injection in injections:
            if injection.injector.type == DPMInjectionType.POINT:
                data[injection.name] = self._constructManualInjection(injection.injector.pointInjection)
            else:
                if injection.injector.type == DPMInjectionType.SURFACE:
                    data[injection.name] = self._constructPatchInjection(injection.injector.surfaceInjection)
                else:
                    data[injection.name] = self._constructConeInjection(injection.injector.coneInjection)

                data[injection.name].update(self._constructFlowRate(injection.injector.flowRate))

            data[injection.name]['massFlowRate'] = '0.8e-03'
            data[injection.name]['sizeDistribution'] = self._constructSizeDistribution(injection.diameterDistribution)

        return data

    def _constructMultiInteractionCoeff(self):
        data = {
            'oneInteractionOnly': 'true',
        }

        localPatches = []
        for bcid, name, ptype in self._db.getBoundaryConditions(''):
            if ptype == BoundaryType.WALL.value:
                interaction = BoundaryManager.wallInteraction(bcid)
                type_ = interaction.type
            else:
                type_ = WallInteractionType.NONE

            if type_ == WallInteractionType.RECYCLE:
                data['model_' + name] = {
                    'patchInteractionModel': 'recycleInteraction',
                    'recycleInteractionCoeffs': {
                        'recyclePatches': [[name, BoundaryDB.getBoundaryName(interaction.recycle.recycleBoundary)]],
                        'recycleFraction': self._helper.pFloatValue(interaction.recycle.recycleFraction),
                    }
                }

                type_ = WallInteractionType.NONE

            localPatches.append(name)
            if type_ == WallInteractionType.NONE:
                localPatches.append({
                    'type': 'none'
                })
            elif interaction.type == WallInteractionType.REFLECT:
                localPatches.append({
                    'type': 'rebound',
                    'e': self._helper.pFloatValue(interaction.reflect.normal),
                    'mu': self._helper.pFloatValue(interaction.reflect.tangential),
                })
            elif interaction.type == WallInteractionType.ESCAPE:
                localPatches.append({
                    'type': 'escape'
                })
            elif interaction.type == WallInteractionType.TRAP:
                localPatches.append({
                    'type': 'stick'
                })

        if localPatches:
            data['localInteractionModel'] = {
                'patchInteractionModel': 'localInteraction',
                'localInteractionCoeffs': {
                    'patches': localPatches
                }
            }

        return data