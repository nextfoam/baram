#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb


class InitializationDB:
    INITIAL_VALUES_XPATH = './/initialization/initialValues'

    @classmethod
    def getPressure(cls):
        db = coredb.CoreDB()
        return float(db.getValue(cls.INITIAL_VALUES_XPATH + '/pressure'))\
            + float(db.getValue('.//operatingConditions/pressure'))

    @classmethod
    def getTemperature(cls):
        return float(coredb.CoreDB().getValue(cls.INITIAL_VALUES_XPATH + '/temperature'))

    @classmethod
    def getScaleOfVelocity(cls):
        return float(coredb.CoreDB().getValue(cls.INITIAL_VALUES_XPATH + '/scaleOfVelocity'))

    @classmethod
    def getTurbulentViscosity(cls):
        return float(coredb.CoreDB().getValue(cls.INITIAL_VALUES_XPATH + '/turbulentViscosity'))

    @classmethod
    def getTurbulentIntensity(cls):
        return float(coredb.CoreDB().getValue(cls.INITIAL_VALUES_XPATH + '/turbulentIntensity')) / 100.0
