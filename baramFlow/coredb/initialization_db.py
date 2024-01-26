#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb import coredb


class InitializationDB:
    @classmethod
    def getVelocity(cls, rname: str) -> float:
        db = coredb.CoreDB()
        return db.getVector(f'.//regions/region[name="{rname}"]/initialization/initialValues/velocity')

    @classmethod
    def getPressure(cls, rname: str) -> float:
        db = coredb.CoreDB()
        return float(db.retrieveValue(f'.//regions/region[name="{rname}"]/initialization/initialValues/pressure'))\
            + float(db.retrieveValue('.//operatingConditions/pressure'))

    @classmethod
    def getGaugePressure(cls, rname: str) -> float:
        db = coredb.CoreDB()
        return float(db.retrieveValue(f'.//regions/region[name="{rname}"]/initialization/initialValues/pressure'))

    @classmethod
    def getTemperature(cls, rname: str) -> float:
        return float(
            coredb.CoreDB().retrieveValue(
                f'.//regions/region[name="{rname}"]/initialization/initialValues/temperature'))

    @classmethod
    def getScaleOfVelocity(cls, rname: str) -> float:
        return float(
            coredb.CoreDB().retrieveValue(
                f'.//regions/region[name="{rname}"]/initialization/initialValues/scaleOfVelocity'))

    @classmethod
    def getTurbulentViscosity(cls, rname: str) -> float:
        return float(
            coredb.CoreDB().retrieveValue(
                f'.//regions/region[name="{rname}"]/initialization/initialValues/turbulentViscosity'))

    @classmethod
    def getTurbulentIntensity(cls, rname: str) -> float:
        return float(
            coredb.CoreDB().retrieveValue(
                f'.//regions/region[name="{rname}"]/initialization/initialValues/turbulentIntensity')) / 100.0
