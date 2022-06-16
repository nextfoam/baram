#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QCoreApplication

from coredb import coredb


class MultiphaseModel(Enum):
    OFF = "off"
    VOLUME_OF_FLUID = "volumeOfFluid"


class TurbulenceModel(Enum):
    INVISCID = "inviscid"
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
    ENERGY_MODELS_PATH = MODELS_XPATH + '/energyModels'

    _multiphaseModelText = {
        MultiphaseModel.OFF: QCoreApplication.translate("ModelsDB", "Off"),
        MultiphaseModel.VOLUME_OF_FLUID: QCoreApplication.translate("ModelsDB", "Volume of Fluid"),
    }

    _turbulenceModelText = {
        TurbulenceModel.INVISCID: QCoreApplication.translate("ModelsDB", "Inviscid"),
        TurbulenceModel.LAMINAR: QCoreApplication.translate("ModelsDB", "Laminar"),
        TurbulenceModel.SPALART_ALLMARAS: QCoreApplication.translate("ModelsDB", "Spalart-Allmaras"),
        TurbulenceModel.K_EPSILON: QCoreApplication.translate("ModelsDB", "k-epsilon"),
        TurbulenceModel.K_OMEGA: QCoreApplication.translate("ModelsDB", "k-omega"),
        TurbulenceModel.LES: QCoreApplication.translate("ModelsDB", "LES"),
    }

    _db = coredb.CoreDB()

    @classmethod
    def getMultiphaseModel(cls):
        return MultiphaseModel(cls._db.getValue(ModelsDB.MULTIPHASE_MODELS_PATH + '/model'))

    @classmethod
    def getMultiphaseModelText(cls):
        return cls._multiphaseModelText[cls.getMultiphaseModel()]

    @classmethod
    def getTurbulenceModel(cls):
        return TurbulenceModel(cls._db.getValue(ModelsDB.TURBULENCE_MODELS_PATH + '/model'))

    @classmethod
    def getTurbulenceModelText(cls):
        return cls._turbulenceModelText[cls.getTurbulenceModel()]

    @classmethod
    def getKEpsilonModel(cls, dbText):
        return KEpsilonModel(dbText)

    @classmethod
    def getNearWallTreatment(cls, dbText):
        return NearWallTreatment(dbText)

    @classmethod
    def getKOmegaModel(cls, dbText):
        return KOmegaModel(dbText)

    @classmethod
    def isMultiphaseModelOn(cls):
        return cls.getMultiphaseModel() != 'off'

    @classmethod
    def isRadiationModelOn(cls):
        return True

    @classmethod
    def isSpeciesModelOn(cls):
        return cls._db.getValue(ModelsDB.SPECIES_MODELS_PATH) != 'off'

    @classmethod
    def isEnergyModelOn(cls):
        return cls._db.getValue(ModelsDB.ENERGY_MODELS_PATH) == 'on'


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
        TurbulenceModel.INVISCID: [],
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

    @classmethod
    def getFields(cls):
        return [cls._fields[f] for f in cls._modelFields[ModelsDB.getTurbulenceModel()]]
