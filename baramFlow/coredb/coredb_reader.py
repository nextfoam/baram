#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb import ValueException, Error, _CoreDB
from baramFlow.coredb.material_db import MaterialDB, UNIVERSAL_GAL_CONSTANT, Phase
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB


class Region:
    def __init__(self, db, rname):
        self._rname = rname

        self._mid = RegionDB.getMaterial(rname)
        self._secondaryMaterials = RegionDB.getSecondaryMaterials(rname)
        self._phase = MaterialDB.getPhase(self._mid)
        self._boundaries = db.getBoundaryConditions(self._rname)

        self._U = None
        self._t = None
        self._rho = None

        self._nut = None
        self._alphat = None
        self._k = None
        self._e = None
        self._w = None

        xpath = RegionDB.getXPath(rname)

        self._U = db.getVector(f'{xpath}/initialization/initialValues/velocity')
        self._t = float(db.getValue(f'{xpath}/initialization/initialValues/temperature'))

        if self.isFluid():
            p = (float(db.getValue(f'{xpath}/initialization/initialValues/pressure'))
                 + float(db.getValue('.//operatingConditions/pressure')))
            v = float(db.getValue(f'{xpath}/initialization/initialValues/scaleOfVelocity'))
            i = (float(db.getValue(f'{xpath}/initialization/initialValues/turbulentIntensity')) / 100.0)
            b = float(db.getValue(f'{xpath}/initialization/initialValues/turbulentViscosity'))

            self._rho = db.getDensity(self._mid, self._t, p)  # Density
            mu = db.getViscosity(self._mid, self._t)  # Viscosity

            nu = mu / self._rho  # Kinetic Viscosity
            pr = float(db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'))

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
    def initialTemperature(self):
        return self._t

    @property
    def initialVelocity(self):
        return self._U

    @property
    def secondaryMaterials(self):
        return self._secondaryMaterials

    def isFluid(self):
        return self._phase != Phase.SOLID

    def isSolid(self):
        return self._phase == Phase.SOLID


class CoreDBReader(_CoreDB):
    def __init__(self):
        super().__init__()

        self._xmlTree = coredb.CoreDB()._xmlTree
        self._arguments = self.getBatchDefaults()

    def setParameters(self, arguments=None):
        self._arguments = self.getBatchDefaults()
        if arguments:
            self._arguments.update(arguments)

    def getValue(self, xpath):
        value = super().getValue(xpath)
        if value == '' or value[0] != '$':
            return value

        parameter = value[1:]
        value = self._arguments.get(parameter)
        try:
            if self.validate(xpath, value):
                return value
        except ValueException as ex:
            error, message = ex.args
            if error == Error.OUT_OF_RANGE:
                message = 'out of range'
            elif error == Error.FLOAT_ONLY:
                message = 'a float is required'

            raise ValueException(
                error,
                QCoreApplication.translate('CoreDBReader', 'Invalid value({0}) for parameter {1} - {2} for {3}')
                .format(value, parameter, message, xpath))

    def getDensity(self, mid, t: float, p: float) -> float:
        xpath = MaterialDB.getXPath(mid)
        spec = self.getValue(xpath + '/density/specification')
        if spec == 'constant':
            return float(self.getValue(xpath + '/density/constant'))
        elif spec == 'perfectGas':
            r'''
            .. math:: \rho = \frac{MW \times P}{R \times T}
            '''
            mw = float(self.getValue(xpath + '/molecularWeight'))
            return p * mw / (UNIVERSAL_GAL_CONSTANT * t)
        elif spec == 'polynomial':
            coeffs = list(map(float, self.getValue(xpath + '/density/polynomial').split()))
            rho = 0.0
            for exp, c in enumerate(coeffs):
                rho += c * t ** exp
            return rho
        else:
            raise KeyError

    def getViscosity(self, mid: int, t: float) -> float:
        xpath = MaterialDB.getXPath(mid)
        spec = self.getValue(xpath + '/viscosity/specification')
        if spec == 'constant':
            return float(self.getValue(xpath + '/viscosity/constant'))
        elif spec == 'polynomial':
            coeffs = list(map(float, self.getValue(xpath + '/viscosity/polynomial').split()))
            mu = 0.0
            for exp, c in enumerate(coeffs):
                mu += c * t ** exp
            return mu
        elif spec == 'sutherland':
            r'''
            .. math:: \mu = \frac{C_1 T^{3/2}}{T+S}
            '''
            c1 = float(self.getValue(xpath + '/viscosity/sutherland/coefficient'))
            s = float(self.getValue(xpath + '/viscosity/sutherland/temperature'))
            return c1 * t ** 1.5 / (t+s)
        else:
            raise KeyError

    def getSpecificHeat(self, mid, t: float) -> float:
        xpath = MaterialDB.getXPath(mid)
        spec = self.getValue(xpath + '/specificHeat/specification')
        if spec == 'constant':
            return float(self.getValue(xpath + '/specificHeat/constant'))
        elif spec == 'polynomial':
            coeffs = list(map(float, self.getValue(xpath + '/specificHeat/polynomial').split()))
            cp = 0.0
            for exp, c in enumerate(coeffs):
                cp += c * t ** exp
            return cp
        else:
            raise KeyError

    def getMolecularWeight(self, mid) -> float:
        return float(self.getValue(MaterialDB.getXPath(mid) + '/molecularWeight'))

    def getRegionProperties(self, rname):
        return Region(self, rname)
