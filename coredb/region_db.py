#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.material_db import MaterialDB, Phase
from coredb.initialization_db import InitializationDB
from coredb.models_db import ModelsDB


DEFAULT_REGION_NAME = 'region0'


class RegionDB:
    class Region:
        def __init__(self, rname):
            self._rname = rname

            self._mid = RegionDB.getMaterial(rname)
            self._secondaryMaterials = RegionDB.getSecondaryMaterials(rname)
            self._phase = MaterialDB.getPhase(self._mid)
            self._boundaries = coredb.CoreDB().getBoundaryConditions(self._rname)

            self._rho = None

            self._nut = None
            self._alphat = None
            self._k = None
            self._e = None
            self._w = None

            if self.isFluid():
                p = InitializationDB.getPressure(rname)
                t = InitializationDB.getTemperature(rname)
                v = InitializationDB.getScaleOfVelocity(rname)
                i = InitializationDB.getTurbulentIntensity(rname)
                b = InitializationDB.getTurbulentViscosity(rname)

                self._rho = MaterialDB.getDensity(self._mid, t, p)  # Density
                mu = MaterialDB.getViscosity(self._mid, t)  # Viscosity

                nu = mu / self._rho  # Kinetic Viscosity
                pr = float(coredb.CoreDB().getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'))

                self._nut = b * nu

                self._alphat = self._rho * self._nut / pr

                self._k = 1.5 * (v*i) ** 2
                self._e = 0.09 * self._k ** 2 / self._nut
                self._w = self._k / self._nut

        @property
        def boundaries(self):
            return self._boundaries

        @property
        def rname(self):
            return self._rname

        @property
        def mid(self):
            return self._mid

        @property
        def phase(self):
            return self._phase

        @property
        def density(self):
            return self._rho

        @property
        def initialNut(self):
            return self._nut

        @property
        def initialAlphat(self):
            return self._alphat

        @property
        def initialK(self):
            return self._k

        @property
        def initialEpsilon(self):
            return self._e

        @property
        def initialOmega(self):
            return self._w

        @property
        def secondaryMaterials(self):
            return self._secondaryMaterials

        def isFluid(self):
            return self._phase & Phase.FLUID

    @classmethod
    def getXPath(cls, rname):
        return f'.//region[name="{rname}"]'

    @classmethod
    def getPhase(cls, rname):
        return MaterialDB.getPhase(coredb.CoreDB().getValue(cls.getXPath(rname) + '/material'))

    @classmethod
    def getMaterial(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/material')

    @classmethod
    def getSecondaryMaterials(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/secondaryMaterials').split()

    @classmethod
    def getRegionProperties(cls, rname):
        return cls.Region(rname)

    @classmethod
    def getSurfaceTensionList(cls, rname) -> list[(str, str, str)]:
        """Returns surface tension list

        Returns a list of surface tension between materials in specified region

        Returns:
            List of surface tension, '(mid1, mis2, surfaceTension)'
        """
        db = coredb.CoreDB()
        xpath = cls.getXPath(rname)

        mids1 = db.getValue(xpath + '/phaseInteractions/surfaceTensions/material1').split()
        mids2 = db.getValue(xpath + '/phaseInteractions/surfaceTensions/material2').split()
        surfaceTensions = db.getValue(xpath + '/phaseInteractions/surfaceTensions/surfaceTension').split()

        return [(mids1[i], mids2[i], surfaceTensions[i]) for i in range(len(surfaceTensions))]
