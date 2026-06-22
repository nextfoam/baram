#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb import _CoreDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel


class KEpsilonSpecification(Enum):
    K_AND_EPSILON                   = 'kAndEpsilon'
    INTENSITY_AND_VISCOSITY_RATIO   = 'intensityAndViscosityRatio'


class KOmegaSpecification(Enum):
    K_AND_OMEGA                     = 'kAndOmega'
    INTENSITY_AND_VISCOSITY_RATIO   = 'intensityAndViscosityRatio'


@dataclass
class KOmega:
    specification: KOmegaSpecification
    turbulentKineticEnergy: str     = None
    specificDissipationRate: str    = None
    turbulentIntensity: str         = None
    turbulentViscosityRatio: str    = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        xpath = BoundaryDB.getXPath(bcid) + '/turbulence/k-omega'

        db.setValue(xpath + '/specification', self.specification.value)
        if self.specification == KOmegaSpecification.K_AND_OMEGA:
            db.setValue(xpath + '/turbulentKineticEnergy', self.turbulentKineticEnergy)
            db.setValue(xpath + '/specificDissipationRate', self.specificDissipationRate)
        elif self.specification == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO:
            db.setValue(xpath + '/turbulentIntensity', self.turbulentIntensity)
            db.setValue(xpath + '/turbulentViscosityRatio', self.turbulentViscosityRatio)


@dataclass
class TransitionSST:
    intermittency: str
    momentumThicknessRe: str

    def applyToDB(self, db: _CoreDB, bcid: str):
        xpath = BoundaryDB.getXPath(bcid) + '/turbulence/transitionSST'

        db.setValue(xpath + '/intermittency', self.intermittency)
        db.setValue(xpath + '/momentumThicknessRe', self.momentumThicknessRe)


@dataclass
class BoundaryTurbulenceUpdate:
    @property
    def model(self):
        raise NotImplementedError

    def applyToDB(self, db: _CoreDB, bcid: str):
        raise NotImplementedError


@dataclass
class BoundaryKOmega(BoundaryTurbulenceUpdate):
    kOmega: KOmega

    @property
    def model(self):
        return TurbulenceModel.K_OMEGA

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.kOmega.applyToDB(db, bcid)


@dataclass
class BoundaryTransitionSST(BoundaryTurbulenceUpdate):
    kOmega: KOmega
    transitionSST: TransitionSST

    @property
    def model(self):
        return TurbulenceModel.TRANSITION_SST

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.kOmega.applyToDB(db, bcid)
        self.transitionSST.applyToDB(db, bcid)
