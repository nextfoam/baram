#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb


class InitializationDB:
    @classmethod
    def getVelocity(cls, region: str) -> float:
        db = coredb.CoreDB()
        return db.getVector(f'.//regions/region[name="{region}"]/initialization/initialValues/velocity')

    @classmethod
    def getPressure(cls, region: str) -> float:
        db = coredb.CoreDB()
        return float(db.getValue(f'.//regions/region[name="{region}"]/initialization/initialValues/pressure'))\
            + float(db.getValue('.//operatingConditions/pressure'))

    @classmethod
    def getTemperature(cls, region: str) -> float:
        return float(coredb.CoreDB().getValue(f'.//regions/region[name="{region}"]/initialization/initialValues/temperature'))

    @classmethod
    def getScaleOfVelocity(cls, region: str) -> float:
        return float(coredb.CoreDB().getValue(f'.//regions/region[name="{region}"]/initialization/initialValues/scaleOfVelocity'))

    @classmethod
    def getTurbulentViscosity(cls, region: str) -> float:
        return float(coredb.CoreDB().getValue(f'.//regions/region[name="{region}"]/initialization/initialValues/turbulentViscosity'))

    @classmethod
    def getTurbulentIntensity(cls, region: str) -> float:
        return float(coredb.CoreDB().getValue(f'.//regions/region[name="{region}"]/initialization/initialValues/turbulentIntensity')) / 100.0
