#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from enum import Enum
from xml.etree.ElementTree import Element

from libbaram.pfloat import PFloat

from baramFlow.coredb.libdb import nsmap, xmlToBool, E


class PressureVelocityCouplingScheme(Enum):
    SIMPLE = 'SIMPLE'
    SIMPLEC = 'SIMPLEC'


class Formulation(Enum):
    IMPLICIT = 'implicit'
    EXPLICIT = 'explicit'


class FluxType(Enum):
    ROE_FDS = 'roeFlux'
    AUSM = 'AUSMplusFlux'
    AUSM_UP = 'AUSMplusUpFlux'


class ImplicitDiscretizationScheme(Enum):
    FIRST_ORDER_IMPLICIT = 'firstOrderImplicit'
    SECOND_ORDER_IMPLICIT = 'secondOrderImplicit'


class InterpolationScheme(Enum):
    LINEAR = 'linear'
    MOMENTUM_WEIGHTED_RECONSTRUC = 'momentumWeightedReconstruct'
    MOMENTUM_WEIGHTED = 'momentumWeighted'


class UpwindDiscretizationScheme(Enum):
    FIRST_ORDER_UPWIND = 'firstOrderUpwind'
    SECOND_ORDER_UPWIND = 'secondOrderUpwind'


@dataclass
class DensityBasedSolverParameters:
    formulation: Formulation        = Formulation.IMPLICIT
    fluxType: FluxType              = FluxType.ROE_FDS
    entropyFixCoefficient: PFloat   = field(default_factory=lambda: PFloat('0.5'))
    cutOffMachNumber: PFloat        = field(default_factory=lambda: PFloat('0.729'))

    @staticmethod
    def fromElement(e: Element):
        return DensityBasedSolverParameters(
            formulation=Formulation(e.find('formulation', namespaces=nsmap).text),
            fluxType=FluxType(e.find('fluxType', namespaces=nsmap).text),
            entropyFixCoefficient=PFloat.fromElement(e.find('entropyFixCoefficient', namespaces=nsmap)),
            cutOffMachNumber=PFloat.fromElement(e.find('cutOffMachNumber', namespaces=nsmap)))

    def toElement(self):
        return E('densityBasedSolverParameters',
                 E('formulation', self.formulation),
                 E('fluxType', self.fluxType),
                 self.entropyFixCoefficient.toElement('entropyFixCoefficient'),
                 self.cutOffMachNumber.toElement('cutOffMachNumber'))


@dataclass(kw_only=True)
class DiscretizationSchemes:
    time: ImplicitDiscretizationScheme                  = ImplicitDiscretizationScheme.FIRST_ORDER_IMPLICIT
    crankNicolsonBlendingFactor: PFloat                 = field(default_factory=lambda: PFloat('0.9'))
    momentum: UpwindDiscretizationScheme                = UpwindDiscretizationScheme.SECOND_ORDER_UPWIND
    energy: UpwindDiscretizationScheme                  = UpwindDiscretizationScheme.SECOND_ORDER_UPWIND
    turbulentKineticEnergy: UpwindDiscretizationScheme  = UpwindDiscretizationScheme.FIRST_ORDER_UPWIND
    volumeFraction: UpwindDiscretizationScheme          = UpwindDiscretizationScheme.SECOND_ORDER_UPWIND
    pressure: InterpolationScheme                       = InterpolationScheme.LINEAR
    scalar: UpwindDiscretizationScheme                  = UpwindDiscretizationScheme.SECOND_ORDER_UPWIND
    species: UpwindDiscretizationScheme                 = UpwindDiscretizationScheme.SECOND_ORDER_UPWIND

    @staticmethod
    def fromElement(e: Element):
        return DiscretizationSchemes(
            time=ImplicitDiscretizationScheme(e.find('time', namespaces=nsmap).text),
            crankNicolsonBlendingFactor=PFloat.fromElement(e.find('crankNicolsonBlendingFactor', namespaces=nsmap)),
            momentum=UpwindDiscretizationScheme(e.find('momentum', namespaces=nsmap).text),
            energy=UpwindDiscretizationScheme(e.find('energy', namespaces=nsmap).text),
            turbulentKineticEnergy=UpwindDiscretizationScheme(
                e.find('turbulentKineticEnergy', namespaces=nsmap).text),
            volumeFraction=UpwindDiscretizationScheme(e.find('volumeFraction', namespaces=nsmap).text),
            pressure=InterpolationScheme(e.find('pressure', namespaces=nsmap).text),
            scalar=UpwindDiscretizationScheme(e.find('scalar', namespaces=nsmap).text),
            species=UpwindDiscretizationScheme(e.find('species', namespaces=nsmap).text))

    def toElement(self):
        return E('discretizationSchemes',
                 E('time', self.time),
                 self.crankNicolsonBlendingFactor.toElement('crankNicolsonBlendingFactor'),
                 E('momentum', self.momentum),
                 E('energy', self.energy),
                 E('turbulentKineticEnergy', self.turbulentKineticEnergy),
                 E('volumeFraction', self.volumeFraction),
                 E('pressure', self.pressure),
                 E('scalar', self.scalar),
                 E('species', self.species))


@dataclass
class UnderRelaxationFactors:
    pressure: PFloat            = field(default_factory=lambda: PFloat('0.3'))
    pressureFinal: PFloat       = field(default_factory=lambda: PFloat('1'))
    density: PFloat             = field(default_factory=lambda: PFloat('0.9'))
    densityFinal: PFloat        = field(default_factory=lambda: PFloat('1'))
    momentum: PFloat            = field(default_factory=lambda: PFloat('0.7'))
    momentumFinal: PFloat       = field(default_factory=lambda: PFloat('1'))
    energy: PFloat              = field(default_factory=lambda: PFloat('1.0'))
    energyFinal: PFloat         = field(default_factory=lambda: PFloat('1'))
    turbulence: PFloat          = field(default_factory=lambda: PFloat('0.7'))
    turbulenceFinal: PFloat     = field(default_factory=lambda: PFloat('1'))
    volumeFraction: PFloat      = field(default_factory=lambda: PFloat('0.7'))
    volumeFractionFinal: PFloat = field(default_factory=lambda: PFloat('1'))
    scalar: PFloat              = field(default_factory=lambda: PFloat('0.7'))
    scalarFinal: PFloat         = field(default_factory=lambda: PFloat('1'))
    species: PFloat             = field(default_factory=lambda: PFloat('1.0'))
    speciesFinal: PFloat        = field(default_factory=lambda: PFloat('1'))

    @staticmethod
    def fromElement(e: Element):
        return UnderRelaxationFactors(
            pressure=PFloat.fromElement(e.find('pressure', namespaces=nsmap)),
            pressureFinal=PFloat.fromElement(e.find('pressureFinal', namespaces=nsmap)),
            density=PFloat.fromElement(e.find('density', namespaces=nsmap)),
            densityFinal=PFloat.fromElement(e.find('densityFinal', namespaces=nsmap)),
            momentum=PFloat.fromElement(e.find('momentum', namespaces=nsmap)),
            momentumFinal=PFloat.fromElement(e.find('momentumFinal', namespaces=nsmap)),
            energy=PFloat.fromElement(e.find('energy', namespaces=nsmap)),
            energyFinal=PFloat.fromElement(e.find('energyFinal', namespaces=nsmap)),
            turbulence=PFloat.fromElement(e.find('turbulence', namespaces=nsmap)),
            turbulenceFinal=PFloat.fromElement(e.find('turbulenceFinal', namespaces=nsmap)),
            volumeFraction=PFloat.fromElement(e.find('volumeFraction', namespaces=nsmap)),
            volumeFractionFinal=PFloat.fromElement(e.find('volumeFractionFinal', namespaces=nsmap)),
            scalar=PFloat.fromElement(e.find('scalar', namespaces=nsmap)),
            scalarFinal=PFloat.fromElement(e.find('scalarFinal', namespaces=nsmap)),
            species=PFloat.fromElement(e.find('species', namespaces=nsmap)),
            speciesFinal=PFloat.fromElement(e.find('speciesFinal', namespaces=nsmap)))

    def toElement(self):
        return E('underRelaxationFactors',
                 self.pressure.toElement('pressure'),
                 self.pressureFinal.toElement('pressureFinal'),
                 self.density.toElement('density'),
                 self.densityFinal.toElement('densityFinal'),
                 self.momentum.toElement('momentum'),
                 self.momentumFinal.toElement('momentumFinal'),
                 self.energy.toElement('energy'),
                 self.energyFinal.toElement('energyFinal'),
                 self.turbulence.toElement('turbulence'),
                 self.turbulenceFinal.toElement('turbulenceFinal'),
                 self.volumeFraction.toElement('volumeFraction'),
                 self.volumeFractionFinal.toElement('volumeFractionFinal'),
                 self.scalar.toElement('scalar'),
                 self.scalarFinal.toElement('scalarFinal'),
                 self.species.toElement('species'),
                 self.speciesFinal.toElement('speciesFinal'))


@dataclass
class HighOrderTermRelaxation:
    disabled: bool              = True
    relaxationFactor: PFloat    = field(default_factory=lambda: PFloat('0.5'))

    @staticmethod
    def fromElement(e: Element):
        return HighOrderTermRelaxation(
            disabled=xmlToBool(e.get('disabled')),
            relaxationFactor=PFloat.fromElement(e.find('relaxationFactor', namespaces=nsmap)))

    def toElement(self):
        return E('highOrderTermRelaxation',
                 self.relaxationFactor.toElement('relaxationFactor'),
                 disabled=self.disabled)


@dataclass
class MultiPhase:
    maxIterationsPerTimeStep: str           = '2'
    numberOfCorrectors: str                 = '1'
    useSemiImplicitMules: bool              = True
    phaseInterfaceCompressionFactor: PFloat = field(default_factory=lambda: PFloat('1'))
    numberOfMulesIterations: str            = '3'

    @staticmethod
    def fromElement(e: Element):
        return MultiPhase(
            maxIterationsPerTimeStep=e.find('maxIterationsPerTimeStep', namespaces=nsmap).text,
            numberOfCorrectors=e.find('numberOfCorrectors', namespaces=nsmap).text,
            useSemiImplicitMules=xmlToBool(e.find('useSemiImplicitMules', namespaces=nsmap).text),
            phaseInterfaceCompressionFactor=PFloat.fromElement(
                e.find('phaseInterfaceCompressionFactor', namespaces=nsmap)),
            numberOfMulesIterations=e.find('numberOfMulesIterations', namespaces=nsmap).text)

    def toElement(self):
        return E('multiphase',
                 E('maxIterationsPerTimeStep', self.maxIterationsPerTimeStep),
                 E('numberOfCorrectors', self.numberOfCorrectors),
                 E('useSemiImplicitMules', self.useSemiImplicitMules),
                 self.phaseInterfaceCompressionFactor.toElement('phaseInterfaceCompressionFactor'),
                 E('numberOfMulesIterations', self.numberOfMulesIterations))


@dataclass
class ConvergenceCriteriaItem:
    absolute: PFloat    = field(default_factory=lambda: PFloat('0.001'))
    relative: PFloat    = field(default_factory=lambda: PFloat('0.05'))

    @staticmethod
    def fromElement(e: Element):
        return ConvergenceCriteriaItem(
            absolute=PFloat.fromElement(e.find('absolute', namespaces=nsmap)),
            relative=PFloat.fromElement(e.find('relative', namespaces=nsmap)))

    def toElement(self, tag: str):
        return E(tag,
                 self.absolute.toElement('absolute'),
                 self.relative.toElement('relative'))


@dataclass
class ConvergenceCriteria:
    pressure: ConvergenceCriteriaItem       = field(default_factory=ConvergenceCriteriaItem)
    density: ConvergenceCriteriaItem        = field(default_factory=ConvergenceCriteriaItem)
    momentum: ConvergenceCriteriaItem       = field(default_factory=ConvergenceCriteriaItem)
    energy: ConvergenceCriteriaItem         = field(default_factory=ConvergenceCriteriaItem)
    turbulence: ConvergenceCriteriaItem     = field(default_factory=ConvergenceCriteriaItem)
    volumeFraction: ConvergenceCriteriaItem = field(default_factory=ConvergenceCriteriaItem)
    scalar: ConvergenceCriteriaItem         = field(default_factory=ConvergenceCriteriaItem)
    species: ConvergenceCriteriaItem        = field(default_factory=ConvergenceCriteriaItem)

    @staticmethod
    def fromElement(e: Element):
        return ConvergenceCriteria(
            pressure=ConvergenceCriteriaItem.fromElement(e.find('pressure', namespaces=nsmap)),
            density=ConvergenceCriteriaItem.fromElement(e.find('density', namespaces=nsmap)),
            momentum=ConvergenceCriteriaItem.fromElement(e.find('momentum', namespaces=nsmap)),
            energy=ConvergenceCriteriaItem.fromElement(e.find('energy', namespaces=nsmap)),
            turbulence=ConvergenceCriteriaItem.fromElement(e.find('turbulence', namespaces=nsmap)),
            volumeFraction=ConvergenceCriteriaItem.fromElement(e.find('volumeFraction', namespaces=nsmap)),
            scalar=ConvergenceCriteriaItem.fromElement(e.find('scalar', namespaces=nsmap)),
            species=ConvergenceCriteriaItem.fromElement(e.find('species', namespaces=nsmap)))

    def toElement(self):
        return E('convergenceCriteria',
                 self.pressure.toElement('pressure'),
                 self.density.toElement('density'),
                 self.momentum.toElement('momentum'),
                 self.energy.toElement('energy'),
                 self.turbulence.toElement('turbulence'),
                 self.volumeFraction.toElement('volumeFraction'),
                 self.scalar.toElement('scalar'),
                 self.species.toElement('species'))


@dataclass
class NumericalLimits:
    minimumStaticTemperature: PFloat    = field(default_factory=lambda: PFloat('1'))
    maximumStaticTemperature: PFloat    = field(default_factory=lambda: PFloat('5000'))
    maximumViscosityRatio: PFloat       = field(default_factory=lambda: PFloat('1e5'))

    @staticmethod
    def fromElement(e: Element):
        return NumericalLimits(
            minimumStaticTemperature=PFloat.fromElement(e.find('minimumStaticTemperature', namespaces=nsmap)),
            maximumStaticTemperature=PFloat.fromElement(e.find('maximumStaticTemperature', namespaces=nsmap)),
            maximumViscosityRatio=PFloat.fromElement(e.find('maximumViscosityRatio', namespaces=nsmap)))

    def toElement(self):
        return E('limits',
                 self.minimumStaticTemperature.toElement('minimumStaticTemperature'),
                 self.maximumStaticTemperature.toElement('maximumStaticTemperature'),
                 self.maximumViscosityRatio.toElement('maximumViscosityRatio'))


@dataclass
class EnergyEquation:
    disabled: bool                          = False
    includeViscousDissipationTerms: bool    = False
    includeKineticEnergyTerms: bool         = False
    includePressureWorkTerms: bool          = True

    @staticmethod
    def fromElement(e: Element):
        return EnergyEquation(
            disabled=xmlToBool(e.get('disabled')),
            includeViscousDissipationTerms=xmlToBool(e.find('includeViscousDissipationTerms', namespaces=nsmap).text),
            includeKineticEnergyTerms=xmlToBool(e.find('includeKineticEnergyTerms', namespaces=nsmap).text),
            includePressureWorkTerms=xmlToBool(e.find('includePressureWorkTerms', namespaces=nsmap).text))

    def toElement(self):
        return E('energy',
                 E('includeViscousDissipationTerms', self.includeViscousDissipationTerms),
                 E('includeKineticEnergyTerms', self.includeKineticEnergyTerms),
                 E('includePressureWorkTerms', self.includePressureWorkTerms),
                 disabled=self.disabled)


@dataclass
class NumericalEquations:
    flow: bool              = True
    energy: EnergyEquation  = field(default_factory=EnergyEquation)
    UDS: bool               = True
    species: bool           = True

    @staticmethod
    def fromElement(e: Element):
        return NumericalEquations(
            flow=xmlToBool(e.find('flow', namespaces=nsmap).text),
            energy=EnergyEquation.fromElement(e.find('energy', namespaces=nsmap)),
            UDS=xmlToBool(e.find('UDS', namespaces=nsmap).text),
            species=xmlToBool(e.find('species', namespaces=nsmap).text))

    def toElement(self):
        return E('equations',
                 E('flow', self.flow),
                 self.energy.toElement(),
                 E('UDS', self.UDS),
                 E('species', self.species))


@dataclass
class CollateralFields:
    age: bool                       = False
    heatTransferCoefficient: bool   = False
    machNumber: bool                = False
    q: bool                         = False
    totalPressure: bool             = False
    vorticity: bool                 = False
    wallHeatFlux: bool              = False
    wallShearStress: bool           = False
    wallYPlus: bool                 = False

    @staticmethod
    def fromElement(e: Element):
        return CollateralFields(
            age=xmlToBool(e.find('age', namespaces=nsmap).text),
            heatTransferCoefficient=xmlToBool(e.find('heatTransferCoefficient', namespaces=nsmap).text),
            machNumber=xmlToBool(e.find('machNumber', namespaces=nsmap).text),
            q=xmlToBool(e.find('q', namespaces=nsmap).text),
            totalPressure=xmlToBool(e.find('totalPressure', namespaces=nsmap).text),
            vorticity=xmlToBool(e.find('vorticity', namespaces=nsmap).text),
            wallHeatFlux=xmlToBool(e.find('wallHeatFlux', namespaces=nsmap).text),
            wallShearStress=xmlToBool(e.find('wallShearStress', namespaces=nsmap).text),
            wallYPlus=xmlToBool(e.find('wallYPlus', namespaces=nsmap).text))

    def toElement(self):
        return E('collateralFields',
                 E('age', self.age),
                 E('heatTransferCoefficient', self.heatTransferCoefficient),
                 E('machNumber', self.machNumber),
                 E('q', self.q),
                 E('totalPressure', self.totalPressure),
                 E('vorticity', self.vorticity),
                 E('wallHeatFlux', self.wallHeatFlux),
                 E('wallShearStress', self.wallShearStress),
                 E('wallYPlus', self.wallYPlus))


@dataclass
class NumericalAdvanced:
    limits: NumericalLimits             = field(default_factory=NumericalLimits)
    equations: NumericalEquations       = field(default_factory=NumericalEquations)
    collateralFields: CollateralFields  = field(default_factory=CollateralFields)

    @staticmethod
    def fromElement(e: Element):
        return NumericalAdvanced(
            limits=NumericalLimits.fromElement(e.find('limits', namespaces=nsmap)),
            equations=NumericalEquations.fromElement(e.find('equations', namespaces=nsmap)),
            collateralFields=CollateralFields.fromElement(e.find('collateralFields', namespaces=nsmap)))

    def toElement(self):
        return E('advanced',
                 self.limits.toElement(),
                 self.equations.toElement(),
                 self.collateralFields.toElement())


@dataclass(kw_only=True)
class NumericalConditions:
    pressureVelocityCouplingScheme: PressureVelocityCouplingScheme  = PressureVelocityCouplingScheme.SIMPLE
    densityBasedSolverParameters: DensityBasedSolverParameters      = field(default_factory=DensityBasedSolverParameters)
    useMomentumPredictor: bool                                      = True
    discretizationSchemes: DiscretizationSchemes                    = field(default_factory=DiscretizationSchemes)
    underRelaxationFactors: UnderRelaxationFactors                  = field(default_factory=UnderRelaxationFactors)
    highOrderTermRelaxation: HighOrderTermRelaxation                = field(default_factory=HighOrderTermRelaxation)
    maxIterationsPerTimeStep: str                                   = '20'
    numberOfCorrectors: str                                         = '4'
    numberOfNonOrthogonalCorrectors: PFloat                         = field(default_factory=lambda: PFloat('0'))
    multiphase: MultiPhase                                          = field(default_factory=MultiPhase)
    convergenceCriteria: ConvergenceCriteria                        = field(default_factory=ConvergenceCriteria)
    advanced: NumericalAdvanced                                     = field(default_factory=NumericalAdvanced)

    @staticmethod
    def fromElement(e: Element):
        return NumericalConditions(
            pressureVelocityCouplingScheme=PressureVelocityCouplingScheme(
                e.find('pressureVelocityCouplingScheme', namespaces=nsmap).text),
            densityBasedSolverParameters=DensityBasedSolverParameters.fromElement(
                e.find('densityBasedSolverParameters', namespaces=nsmap)),
            useMomentumPredictor=xmlToBool(e.find('useMomentumPredictor', namespaces=nsmap).text),
            discretizationSchemes=DiscretizationSchemes.fromElement(e.find('discretizationSchemes', namespaces=nsmap)),
            underRelaxationFactors=UnderRelaxationFactors.fromElement(e.find(
                'underRelaxationFactors', namespaces=nsmap)),
            highOrderTermRelaxation=HighOrderTermRelaxation.fromElement(e.find(
                'highOrderTermRelaxation', namespaces=nsmap)),
            maxIterationsPerTimeStep=e.find('maxIterationsPerTimeStep', namespaces=nsmap).text,
            numberOfCorrectors=e.find('numberOfCorrectors', namespaces=nsmap).text,
            numberOfNonOrthogonalCorrectors=PFloat.fromElement(
                e.find('numberOfNonOrthogonalCorrectors', namespaces=nsmap)),
            multiphase=MultiPhase.fromElement(e.find('multiphase', namespaces=nsmap)),
            convergenceCriteria=ConvergenceCriteria.fromElement(e.find('convergenceCriteria', namespaces=nsmap)),
            advanced=NumericalAdvanced.fromElement(e.find('advanced', namespaces=nsmap)))

    def toElement(self):
        return E('numericalConditions',
                 E('pressureVelocityCouplingScheme', self.pressureVelocityCouplingScheme),
                 self.densityBasedSolverParameters.toElement(),
                 E('useMomentumPredictor', self.useMomentumPredictor),
                 self.discretizationSchemes.toElement(),
                 self.underRelaxationFactors.toElement(),
                 self.highOrderTermRelaxation.toElement(),
                 E('maxIterationsPerTimeStep', self.maxIterationsPerTimeStep),
                 E('numberOfCorrectors', self.numberOfCorrectors),
                 self.numberOfNonOrthogonalCorrectors.toElement('numberOfNonOrthogonalCorrectors'),
                 self.multiphase.toElement(),
                 self.convergenceCriteria.toElement(),
                 self.advanced.toElement())
