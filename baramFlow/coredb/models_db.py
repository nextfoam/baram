#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

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


class ModelsDB:
    MODELS_XPATH = '/models'
    MULTIPHASE_MODELS_XPATH = '/models/multiphaseModels'
    SPECIES_MODELS_XPATH    = '/models/speciesModels'
    ENERGY_MODELS_XPATH     = '/models/energyModels'

    @classmethod
    def getMultiphaseModel(cls):
        return MultiphaseModel(coredb.CoreDB().getValue(ModelsDB.MULTIPHASE_MODELS_XPATH + '/model'))

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
