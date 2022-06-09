#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QCoreApplication

from coredb import coredb


class MultiphaseModel(Enum):
    OFF = "off"
    VOLUME_OF_FLUID = "volumeOfFluid"


class TurbulenceModel(Enum):
    LAMINAR = "laminar"
    SPALART_ALLMARAS = "spalartAllmaras"
    K_EPSILON = "k-epsilon"
    K_OMEGA = "k-omega"
    LES = "les"


class KEpsilonModel(Enum):
    STANDARD = "standard"
    RNG = "rng"
    REALIZABLE = "realizable"


class NearWallTreatment(Enum):
    STANDARD_WALL_FUNCTIONS = "standardWallFunctions"
    ENHANCED_WALL_TREATMENT = "enhancedWallTreatment"


class KOmegaModel(Enum):
    SST = "SST"


class TurbulenceFields(Enum):
    K = auto()
    EPSILON = auto()
    OMEGA = auto()
    NU_TILDA = auto()


class ModelsDB:
    MODELS_XPATH = './/models'
    MULTIPHASE_MODELS_PATH = MODELS_XPATH + '/multiphaseModels'
    TURBULENCE_MODELS_PATH = MODELS_XPATH + '/turbulenceModels'
    SPECIES_MODELS_PATH = MODELS_XPATH + '/speciesModels'

    _multiphaseModelText = {
        MultiphaseModel.OFF: "Off",
        MultiphaseModel.VOLUME_OF_FLUID: "Volume of Fluid",
    }

    _turbulenceModelText = {
        TurbulenceModel.LAMINAR: "Laminar",
        TurbulenceModel.SPALART_ALLMARAS: "Spalart-Allmaras",
        TurbulenceModel.K_EPSILON: "k-epsilon",
        TurbulenceModel.K_OMEGA: "k-omega",
        TurbulenceModel.LES: "les",
    }

    @classmethod
    def getMultiphaseModel(cls, dbText):
        return MultiphaseModel(dbText)

    @classmethod
    def getMuliphaseModelText(cls, model):
        return cls._multiphaseModelText[model]

    @classmethod
    def getTurbulenceModel(cls, dbText):
        return TurbulenceModel(dbText)

    @classmethod
    def getTurbulenceModelText(cls, model):
        return cls._turbulenceModelText[model]

    @classmethod
    def getKEpsilonModel(cls, dbText):
        return KEpsilonModel(dbText)

    @classmethod
    def getNearWallTreatment(cls, dbText):
        return NearWallTreatment(dbText)

    @classmethod
    def getKOmegaModel(cls, dbText):
        return KOmegaModel(dbText)


class TurbulenceField:
    def __init__(self, name, symbol, unit, xpathName):
        self._name = name
        self._symbol = symbol
        self._unit = unit
        self._xpathName = xpathName

    @property
    def xpathName(self):
        return self._xpathName

    def getTitleText(self):
        return f'{self._name}, {self._symbol}'

    def getLabelText(self):
        return f'{self._symbol} ({self._unit})'


class TurbulenceModelHelper:
    _modelFields = {
        TurbulenceModel.LAMINAR: [],
        TurbulenceModel.SPALART_ALLMARAS: [TurbulenceFields.NU_TILDA],
        TurbulenceModel.K_EPSILON: [TurbulenceFields.K, TurbulenceFields.EPSILON],
        TurbulenceModel.K_OMEGA: [TurbulenceFields.K, TurbulenceFields.OMEGA],
        TurbulenceModel.LES: [],
    }

    _fields = {
        TurbulenceFields.K:
            TurbulenceField(QCoreApplication.translate("TurbulenceModel", "Turbulent Kinetic Energy"),
                            "k", "m<sup>2</sup>/s<sup>2</sup>", "turbulentKineticEnergy"),
        TurbulenceFields.EPSILON:
            TurbulenceField(QCoreApplication.translate("TurbulenceModel", "Turbulent Dissipation Rate"),
                            "ε", "m<sup>2</sup>/s<sup>3</sup>", "turbulentDissipationRate"),
        TurbulenceFields.OMEGA:
            TurbulenceField(QCoreApplication.translate("TurbulenceModel", "Specific Dissipation Rate"),
                            "ω", "1/s", "specificDissipationRate"),
        TurbulenceFields.NU_TILDA:
            TurbulenceField(QCoreApplication.translate("TurbulenceModel", "Modified Turbulent Viscosity"),
                            "ν", "m<sup>2</sup>/s", "modifiedTurbulentViscosity"),
    }

    _db = coredb.CoreDB()

    @classmethod
    def getModel(cls):
        return TurbulenceModel(cls._db.getValue(ModelsDB.TURBULENCE_MODELS_PATH + '/model'))

    @classmethod
    def getFields(cls):
        return [cls._fields[f] for f in cls._modelFields[cls.getModel()]]
