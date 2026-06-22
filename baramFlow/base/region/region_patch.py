#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.base.region.region_data import RegionInitialization
from baramFlow.coredb.region_db import RegionDB


@dataclass
class RegionInitializationPatch:
    rname: str

    patch: RegionInitialization

    def applyToDB(self, db):
        path = RegionDB.getXPath(self.rname) + '/initialization/initialValues'

        initialValues = self.patch.initialValues
        db.setValue(path + '/velocity/x', str(initialValues.velocity.x))
        db.setValue(path + '/velocity/y', str(initialValues.velocity.y))
        db.setValue(path + '/velocity/z', str(initialValues.velocity.z))
        db.setValue(path + '/pressure', initialValues.pressure)
        db.setValue(path + '/temperature', initialValues.temperature)
        db.setValue(path + '/scaleOfVelocity', initialValues.scaleOfVelocity)
        db.setValue(path + '/turbulentIntensity', initialValues.turbulentIntensity)
        db.setValue(path + '/turbulentViscosity', initialValues.turbulentViscosity)
        db.setValue(path + '/intermittency', initialValues.intermittency)
        db.setValue(path + '/momentumThicknessRe', initialValues.momentumThicknessRe)
