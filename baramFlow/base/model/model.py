#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QCoreApplication

MODELS_XPATH = '/models'


class Models(Enum):
    TURBULENCE  = auto()
    ENERGY      = auto()
    FLOW_TYPE   = auto()
    MULTIPHASE  = auto()
    SOLVER_TYPE = auto()
    SPECIES     = auto()
    SCALARS     = auto()
    DPM         = auto()


class DPMParticleType(Enum):
    NONE        = 'none'
    INERT       = 'inert'
    DROPLET     = 'droplet'
    COMBUSTING  = 'combusting'


class DPMTrackingScheme(Enum):
    IMPLICIT    = 'implicit'
    ANALYTIC    = 'analytic'


class DPMDragForce(Enum):
    SPHERICAL               = 'spherical'
    NON_SPHERICAL           = 'nonSpherical'
    DISTORTED_SPHERE        = 'distortedSphere'
    WEN_AND_YU              = 'wenAndYu'
    GIDASPOW                = 'gidaspow'
    DU_PIESSIS_AND_MASLIYAH = 'duPlessisAndMasliyah'
    TOMIYAMA                = 'tomiyama'


class DPMLiftForce(Enum):
    NONE        = 'none'
    SAFFMAN_MEI = 'saffmanMei'
    TOMIYAMA    = 'tomiyama'


class DPMTurbulentDispersion(Enum):
    NONE                    = 'none'
    STOCHASTIC_DISPEDRSION  = 'stochasticDispersion'
    GRADIENT_DISPERSION     = 'gradientDispersion'


class DPMHeatTransferSpeicification(Enum):
    NONE            = 'none'
    RANZ_MARHALL    = 'ranzMarshall'


class DPMEvaporationModel(Enum):
    NONE                            = 'none'
    DIFFUSION_CONTROLLED            = 'diffusionControlled'
    CONVECTION_DIFFUSION_CONTROLLED = 'convectionDiffusionControlled'


class DPMEnthalpyTransferType(Enum):
    ENTHALPY_DIFFENENCE = 'enthalpyDifference'
    LATENT_HEAT         = 'latentHeat'


class DPMInjectionType(Enum):
    POINT   = 'point'
    SURFACE = 'surface'
    CONE    = 'cone'


class DPMDiameterDistribution(Enum):
    UNIFORM             = 'uniform'
    LINEAR              = 'linear'
    ROSIN_RAMMLER       = 'rosinRammler'
    MASS_ROSIN_RAMMLER  = 'massRosinRammler'
    NORMAL              = 'normal'


class DPMFlowRateSpec(Enum):
    PARTICLE_COUNT  = 'particleCount'
    PARTICLE_VOLUME = 'particleVolume'


class DPMConeInjectorType(Enum):
    POINT   = 'point'
    DISC    = 'disc'


class DPMParticleSpeed(Enum):
    FROM_INJECTION_SPEED    = 'fromInjectionSpeed'
    FROM_PRESSURE           = 'fromPressure'
    FROM_DISCHARGE_COEFF    = 'fromDischargeCoeff'


class DPMParticleVelocityType(Enum):
    CONSTANT    = 'constant'
    FACE_VALUE  = 'faceValue'
    CELL_VALUE  = 'cellValue'


DPM_INJECTION_TYPE_TEXTS = {
    DPMInjectionType.POINT      : QCoreApplication.translate('DPM', 'Point'),
    DPMInjectionType.SURFACE    : QCoreApplication.translate('DPM', 'Surface'),
    DPMInjectionType.CONE       : QCoreApplication.translate('DPM', 'Cone')
}
