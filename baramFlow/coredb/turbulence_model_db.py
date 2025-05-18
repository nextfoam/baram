#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QCoreApplication, QObject

from baramFlow.coredb import coredb
from .models_db import IndexedEnum


class ITurbulenceModelObserver(QObject):
    def modelUpdating(self, db, model):
        pass


class TurbulenceModel(IndexedEnum):
    INVISCID = 'inviscid'
    LAMINAR = 'laminar'
    SPALART_ALLMARAS = 'spalartAllmaras'
    K_EPSILON = 'k-epsilon'
    K_OMEGA = 'k-omega'
    DES = 'des'
    LES = 'les'


TurbulenceRasModels = {
    TurbulenceModel.SPALART_ALLMARAS,
    TurbulenceModel.K_EPSILON,
    TurbulenceModel.K_OMEGA
}


class KEpsilonModel(IndexedEnum):
    STANDARD = 'standard'
    RNG = 'rng'
    REALIZABLE = 'realizable'


class NearWallTreatment(IndexedEnum):
    STANDARD_WALL_FUNCTIONS = 'standardWallFunctions'
    ENHANCED_WALL_TREATMENT = 'enhancedWallTreatment'


class KOmegaModel(Enum):
    SST = 'SST'


class RANSModel(Enum):
    SPALART_ALLMARAS = 'spalartAllmaras'
    K_OMEGA_SST = 'kOmegaSST'


class ShieldingFunctions(Enum):
    DDES = 'DDES'
    IDDES = 'IDDES'


class SubgridScaleModel(Enum):
    SMAGORINSKY = 'Smagorinsky'
    WALE = 'WALE'
    DYNAMIC_KEQN = 'dynamicKEqn'
    KEQN = 'kEqn'


class LengthScaleModel(Enum):
    CUBE_ROOT_VOLUME = 'cubeRootVol'
    VAN_DRIEST = 'vanDriest'
    SMOOTH = 'smooth'


class SubgridKineticEnergySpecificationMethod(Enum):
    SUBGRID_SCALE_K = 'subgridScaleK'
    SUBGRID_SCALE_INTENSITY = 'subgridScaleIntensity'


class TurbulenceFields(Enum):
    K = auto()
    EPSILON = auto()
    OMEGA = auto()
    NU_TILDA = auto()


class TurbulenceModelsDB:
    TURBULENCE_MODELS_XPATH = '/models/turbulenceModels'

    _RANSToRASModelMap = {
        RANSModel.SPALART_ALLMARAS: TurbulenceModel.SPALART_ALLMARAS,
        RANSModel.K_OMEGA_SST:      TurbulenceModel.K_OMEGA
    }

    _modelObservers = []

    @classmethod
    def registerModelObserver(cls, observer):
        cls._modelObservers.append(observer)

    @classmethod
    def getModel(cls):
        return TurbulenceModel(coredb.CoreDB().getValue(cls.TURBULENCE_MODELS_XPATH + '/model'))

    @classmethod
    def getDESRansModel(cls):
        return (RANSModel(coredb.CoreDB().getValue(cls.TURBULENCE_MODELS_XPATH + '/des/RANSModel'))
                if cls.getModel() == TurbulenceModel.DES else None)

    @classmethod
    def getLESSubgridScaleModel(cls):
        return (SubgridScaleModel(coredb.CoreDB().getValue(cls.TURBULENCE_MODELS_XPATH + '/les/subgridScaleModel'))
                if cls.getModel() == TurbulenceModel.LES else None)

    @classmethod
    def isLESKEqnModel(cls):
        return TurbulenceModelsDB.getLESSubgridScaleModel() in (SubgridScaleModel.DYNAMIC_KEQN, SubgridScaleModel.KEQN)

    @classmethod
    def isLESSpalartAllmarasModel(cls):
        return TurbulenceModelsDB.getLESSubgridScaleModel() in (SubgridScaleModel.SMAGORINSKY, SubgridScaleModel.WALE)

    @classmethod
    def getRASModel(cls):
        turbulenceModel = cls.getModel()
        if turbulenceModel in TurbulenceRasModels:
            return turbulenceModel

        ransModel = TurbulenceModelsDB.getDESRansModel()
        return cls._RANSToRASModelMap[ransModel] if ransModel in cls._RANSToRASModelMap else None

    @classmethod
    def updateModel(cls, db, model):
        if TurbulenceModelsDB.getModel() == model:
            return

        for observer in cls._modelObservers:
            observer.modelUpdating(db, model)

        db.setValue(TurbulenceModelsDB.TURBULENCE_MODELS_XPATH + '/model', model.value)


class TurbulenceField:
    def __init__(self, field, symbol, unit, sourceUnits, xpathName):
        self._field = field
        self._symbol = symbol
        self._unit = unit
        self._sourceUnits = sourceUnits
        self._xpathName = xpathName

    @property
    def xpathName(self):
        return self._xpathName

    @property
    def symbol(self):
        return self._symbol

    @property
    def unit(self):
        return self._unit

    @property
    def sourceUnits(self):
        return self._sourceUnits

    def name(self):
        return {
            TurbulenceFields.K:         QCoreApplication.translate('TurbulenceModel', 'Turbulent Kinetic Energy'),
            TurbulenceFields.EPSILON:   QCoreApplication.translate('TurbulenceModel', 'Turbulent Dissipation Rate'),
            TurbulenceFields.OMEGA:     QCoreApplication.translate('TurbulenceModel', 'Specific Dissipation Rate'),
            TurbulenceFields.NU_TILDA:  QCoreApplication.translate('TurbulenceModel', 'Modified Turbulent Viscosity'),
        }.get(self._field)

    def getLabelText(self):
        return f'{self._symbol} ({self._unit})'
