#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb import coredb


class IndexedEnum(Enum):
    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj.index = len(cls.__members__)
        return obj

    @classmethod
    def byIndex(cls, index):
        for member in cls.__members__.values():
            if member.index == index:
                return member

        raise KeyError(index)


class Models(Enum):
    TURBULENCE  = auto()
    ENERGY      = auto()
    FLOW_TYPE   = auto()
    MULTIPHASE  = auto()
    SOLVER_TYPE = auto()
    SPECIES     = auto()
    SCALARS     = auto()


class MultiphaseModel(Enum):
    OFF = 'off'
    VOLUME_OF_FLUID = 'volumeOfFluid'


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


class ModelsDB:
    MODELS_XPATH = './/models'
    MULTIPHASE_MODELS_XPATH = './/multiphaseModels'
    TURBULENCE_MODELS_XPATH = './/turbulenceModels'
    SPECIES_MODELS_XPATH = './/speciesModels'
    ENERGY_MODELS_XPATH = './/energyModels'

    @classmethod
    def getMultiphaseModel(cls):
        return MultiphaseModel(coredb.CoreDB().getValue(ModelsDB.MULTIPHASE_MODELS_XPATH + '/model'))

    @classmethod
    def getTurbulenceModel(cls):
        return TurbulenceModel(coredb.CoreDB().getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model'))

    @classmethod
    def isMultiphaseModelOn(cls):
        return cls.getMultiphaseModel() != MultiphaseModel.OFF

    @classmethod
    def isRadiationModelOn(cls):
        return False

    @classmethod
    def isSpeciesModelOn(cls):
        return coredb.CoreDB().getValue(ModelsDB.SPECIES_MODELS_XPATH) != 'off'

    @classmethod
    def isEnergyModelOn(cls):
        return coredb.CoreDB().getValue(ModelsDB.ENERGY_MODELS_XPATH) == 'on'

    @classmethod
    def EnergyModelOn(cls):
        coredb.CoreDB().setValue(ModelsDB.ENERGY_MODELS_XPATH, 'on')

    @classmethod
    def EnergyModelOff(cls):
        coredb.CoreDB().setValue(ModelsDB.ENERGY_MODELS_XPATH, 'off')


class TurbulenceModelsDB:
    _RANSToRASModelMap = {
        RANSModel.SPALART_ALLMARAS: TurbulenceModel.SPALART_ALLMARAS,
        RANSModel.K_OMEGA_SST:      TurbulenceModel.K_OMEGA
    }

    @classmethod
    def getTurbulenceModel(cls):
        return ModelsDB.getTurbulenceModel()

    @classmethod
    def getDESRansModel(cls):
        return (RANSModel(coredb.CoreDB().getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/des/RANSModel'))
                if ModelsDB.getTurbulenceModel() == TurbulenceModel.DES else None)

    @classmethod
    def getLESSubgridScaleModel(cls):
        return (SubgridScaleModel(coredb.CoreDB().getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/les/subgridScaleModel'))
                if ModelsDB.getTurbulenceModel() == TurbulenceModel.LES else None)

    @classmethod
    def isLESKEqnModel(cls):
        return TurbulenceModelsDB.getLESSubgridScaleModel() in (SubgridScaleModel.DYNAMIC_KEQN, SubgridScaleModel.KEQN)

    @classmethod
    def isLESSpalartAllmarasModel(cls):
        return TurbulenceModelsDB.getLESSubgridScaleModel() in (SubgridScaleModel.SMAGORINSKY, SubgridScaleModel.WALE)

    @classmethod
    def getRASModel(cls):
        turbulenceModel = ModelsDB.getTurbulenceModel()
        if turbulenceModel in TurbulenceRasModels:
            return turbulenceModel

        ransModel = TurbulenceModelsDB.getDESRansModel()
        return cls._RANSToRASModelMap[ransModel] if ransModel in cls._RANSToRASModelMap else None


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
