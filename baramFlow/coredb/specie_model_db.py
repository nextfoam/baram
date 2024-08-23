#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

from baramFlow.coredb.models_db import ModelsDB


class ISpecieModelObserver(QObject):
    def turningOff(self, db, mixtures):
        pass


class SpecieModelDB:
    _observers = []

    @classmethod
    def registerObserver(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def turnOn(cls, db):
        db.setValue(ModelsDB.SPECIES_MODELS_XPATH, 'on')

    @classmethod
    def turnOff(cls, db):
        mixtures = [mid for mid, _, _, _ in db.getMaterials('mixture')]
        if mixtures:
            for observer in cls._observers:
                observer.turningOff(db, mixtures)

        db.setValue(ModelsDB.SPECIES_MODELS_XPATH, 'off')
