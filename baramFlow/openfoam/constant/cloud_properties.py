#!/usr/bin/env python
# -*- coding:, # utf-8 -*-

from baramFlow.base.material.material import MaterialType, Phase
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile, DataClass

from baramFlow.base.boundary.boundary import BoundaryManager, PatchInteractionType
from baramFlow.base.model.DPM_model import DPMModelManager, KinematicModel, FlowRate, DiameterDistribution, Injection
from baramFlow.base.model.DPM_model import ConeInjection, PointInjection, SurfaceInjection
from baramFlow.base.model.model import DPMEvaporationModel, DPMTrackingScheme, DPMParticleType, DPMTurbulentDispersion, DPMFlowRateSpec
from baramFlow.base.model.model import DPMDragForce, DPMLiftForce, DPMInjectionType, DPMDiameterDistribution
from baramFlow.base.model.model import DPMParticleVelocityType, DPMParticleSpeed
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB, TurbulenceModel
from baramFlow.openfoam.dictionary_helper import DictionaryHelper
from baramFlow.openfoam.file_system import FileSystem


def _getGasName(liquidMid: str, rname: str):
    db = CoreDBReader()

    mid = RegionDB.getMaterial(rname)
    if MaterialDB.getType(mid) != MaterialType.MIXTURE:  # Requirement for SLG Thermo
        return ''

    # Build species table to find a specie corresponding to liquids in the droplet
    species: dict[str, str] = {}  # {<chemicalFormula>: <specieName>}
    for specie, name in MaterialDB.getSpecies(mid).items():
        chemicalFormula = MaterialDB.getChemicalFormula(specie)
        species[chemicalFormula] = name

    chemicalFormula = MaterialDB.getChemicalFormula(liquidMid)

    if chemicalFormula in species:  # It should be in the fluid mixture
        return species[chemicalFormula]  # use the name of corresponding specie in the fluid
    else:
        return ''


class CloudProperties(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'cloudProperties')

        self._rname = rname

        self._helper = DictionaryHelper()
        self._db = CoreDBReader()

    def build(self):
        if self._data is not None:
            return self

        properties = DPMModelManager.properties()

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
                'calcFrequency': self._helper.pFloatValue(properties.numericalConditions.DPMIterationInterval),
                'sourceTerms': {
                    'resetOnStartup': 'false',
                    'schemes': {
                        'rho':       'explicit 1',
                        'U':         'explicit 1',
                        'Yi':        'explicit 1',
                        'h':         'explicit 1',
                        'radiation': 'explicit 1',
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
                    'DUcDt': 'cell',
                    'curlUcDt': 'cell',
                },
                'integrationSchemes': {
                    'U': integrationScheme,
                    'T': integrationScheme
                }
            },
            'constantProperties': {
                'rho0': self._db.getValue(MaterialDB.getXPath(mid) + '/density/constant'),
                'T0': self._helper.pFloatValue(properties.droplet.temperature),
                'Cp0': self._db.getValue(MaterialDB.getXPath(mid) + '/specificHeat/constant'),
            },
            'subModels': {
                'particleForces': self._constructParticleForce(properties.kinematicModel),
                'injectionModels': self._constructInjections(DPMModelManager.injections()),
                'patchInteractionModel': 'multiInteraction',
                'heatTransferModel': properties.heatTransfer.specification.value,
                'RanzMarshallCoeffs': {
                    'BirdCorrection': self._helper.boolValue(properties.heatTransfer.ranzMarsahll.birdCorrection),
                },
                'surfaceFilmModel': 'none',
                'stochasticCollisionModel': 'none',
                'multiInteractionCoeffs': self._constructMultiInteractionCoeff(),
                'phaseChangeModel' : 'none',
                'devolatilisationModel': 'none',
                'surfaceReactionModel': 'none',
                'radiation': 'off',
            },
            'cloudFunctions': self._buildCloudFunctions()
        }

        turbulenceDispersion = (
            DPMTurbulentDispersion.NONE if TurbulenceModelsDB.getModel() != TurbulenceModel.SPALART_ALLMARAS
            else properties.turbulentDispersion)
        self._data['subModels']['dispersionModel'] = turbulenceDispersion.value

        if DPMModelManager.particleType() == DPMParticleType.DROPLET:
            subModels = self._buildReactingSubmodels(properties)
            self._data['subModels'].update(subModels)

        return self

    def _constructParticleForce(self, model: KinematicModel):
        def dragForceDict(specification):
            if specification == DPMDragForce.NON_SPHERICAL:
                return {
                    'phi': self._helper.pFloatValue(model.dragForce.nonSphereDrag.shapeFactor)
                }

            if specification == DPMDragForce.TOMIYAMA:
                return {
                    'sigma': self._helper.pFloatValue(model.dragForce.tomyamaDrag.surfaceTension),
                    'contamination': model.dragForce.tomyamaDrag.contamination.value
                }

            return {}

        def liftForceDict(specification):
            if specification == DPMLiftForce.TOMIYAMA:
                return {
                    'sigma': self._helper.pFloatValue(model.liftForce.tomiyamaLift.surfaceTension),
                }

            return {}

        data = {
            model.dragForce.specification.value: dragForceDict(model.dragForce.specification),
        }

        if model.liftForce.specification != DPMLiftForce.NONE:
            data[model.liftForce.specification.value] = liftForceDict(model.liftForce.specification)

        if model.gravity:
            data['gravity'] = ''

        if model.pressureGradient:
            data['pressureGradient'] = {}

        if not model.brownianMotionForce.disabled \
            and TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR \
                and ModelsDB.isEnergyModelOn():
            data['BrownianMotion'] = {
                'lambda': self._helper.pFloatValue(model.brownianMotionForce.molecularFreePathLength),
                'turbulence': self._helper.boolValue(model.brownianMotionForce.useTurbulence),
                'spherical': 'false'
            }

        return data

    def _constructFlowRate(self, flowRate: FlowRate):
        if GeneralDB.isTimeTransient():
            startTime = self._helper.pFloatValue(flowRate.startTime)
            duration = float(self._helper.pFloatValue(flowRate.stopTime)) - float(startTime)
        else:
            startTime = 0
            duration = 1

        if flowRate.specification == DPMFlowRateSpec.PARTICLE_COUNT:
            return {
                'parcelBasisType': 'fixed',
                'parcelsPerSecond': self._helper.pFloatValue(flowRate.particleCount.parcelPerSecond),
                'nParticle': self._helper.pFloatValue(flowRate.particleCount.numberOfParticlesPerParcel),
                'massTotal': '0',
                'flowRateProfile': self._helper.function1ScalarValue(flowRate.particleVolume.volumeFlowRate),
                'massFlowRate': ('constant', '0'),
                'SOI': startTime,
                'duration': duration
            }
        elif flowRate.specification == DPMFlowRateSpec.PARTICLE_VOLUME:
            return {
                'parcelBasisType': 'mass',
                'parcelsPerSecond': self._helper.pFloatValue(flowRate.particleVolume.parcelPerSecond),
                'massTotal': self._helper.pFloatValue(flowRate.particleVolume.totalMass),
                'flowRateProfile': self._helper.function1ScalarValue(flowRate.particleVolume.volumeFlowRate),
                'massFlowRate': ('constant', self._helper.pFloatValue(flowRate.particleVolume.massFlowRate)),
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
            'nParticle': self._helper.pFloatValue(injection.numberOfParticlesPerPoint),
            'massTotal': '0',
            'massFlowRate': ('constant', '0'),
            'parcelsPerSecond': '1',
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

            data[injection.name]['sizeDistribution'] = self._constructSizeDistribution(injection.diameterDistribution)

        return data

    def _constructMultiInteractionCoeff(self):
        data = {
            'oneInteractionOnly': 'true',
        }

        localPatches = []
        recycles = {}

        for bcid, name, ptype in self._db.getBoundaryConditions(''):
            interaction = BoundaryManager.patchInteraction(str(bcid))
            type_ = interaction.type

            if type_ == PatchInteractionType.RECYCLE:
                recycles['model_' + name] = {
                    'patchInteractionModel': 'recycleInteraction',
                    'recycleInteractionCoeffs': {
                        'recyclePatches': [[name, BoundaryDB.getBoundaryName(interaction.recycle.recycleBoundary)]],
                        'recycleFraction': self._helper.pFloatValue(interaction.recycle.recycleFraction),
                    }
                }
            else:  # localInteraction
                localPatches.append(name)
                if interaction.type == PatchInteractionType.REFLECT:
                    localPatches.append({
                        'type': 'rebound',
                        'e': self._helper.pFloatValue(interaction.reflect.normal),
                        'mu': (1 - float(self._helper.pFloatValue(interaction.reflect.tangential))),
                    })
                elif interaction.type == PatchInteractionType.ESCAPE:
                    localPatches.append({
                        'type': 'escape'
                    })
                elif interaction.type == PatchInteractionType.TRAP:
                    localPatches.append({
                        'type': 'stick'
                    })
                else:  # type_ == PatchInteractionType.NONE
                    localPatches.append({
                        'type': 'none'
                    })

        if localPatches:
            data['localInteractionModel'] = {
                'patchInteractionModel': 'localInteraction',
                'localInteractionCoeffs': {
                    'patches': localPatches
                }
            }

        if recycles:
            data.update(recycles)

        return data

    def _buildReactingSubmodels(self, properties):
        solid = {}
        liquid = {}
        solidTot = 0
        liquidTot = 0
        for material in properties.droplet.composition:
            phase = MaterialDB.getPhase(material.mid)
            composition = float(material.composition)
            if phase == Phase.SOLID:
                solid[MaterialDB.getName(material.mid)] = composition
                solidTot += float(material.composition)
            elif phase == Phase.LIQUID:
                liquid[_getGasName(material.mid, self._rname)] = composition
                liquidTot += float(material.composition)

        subModels = {
            'compositionModel': 'singleMixtureFraction',
            'singleMixtureFractionCoeffs': {
                'phases': [
                    'gas', {},
                    'liquid', {material: round(composition / liquidTot, 6) for material, composition in liquid.items()},
                    'solid', {material: round(composition / solidTot, 6) for material, composition in solid.items()}
                ],
                'YGasTot0': 0,
                'YLiquidTot0': liquidTot,
                'YSolidTot0': solidTot
            },
            'liquidEvaporationCoeffs': {
                'enthalpyTransfer': properties.evaporation.enthalpyTransferType.value,
                'activeLiquids': list(liquid.keys())
            }
        }

        if properties.evaporation.model == DPMEvaporationModel.DIFFUSION_CONTROLLED:
            subModels['phaseChangeModel'] = 'liquidEvaporation'
        elif properties.evaporation.model == DPMEvaporationModel.CONVECTION_DIFFUSION_CONTROLLED:
            subModels['phaseChangeModel'] = 'liquidEvaporationBoil'

        return subModels

    def _buildCloudFunctions(self)->dict:
        if GeneralDB.isTimeTransient():
            return {}
        else:
            return {
                'particleTracks1': {
                    'type': 'particleTracks',
                    'trackInterval': '5',
                    'maxSamples': '1000000',
                    'resetOnWrite': 'yes'
                }
            }
