#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Flag, auto


class Phase(Flag):
    GAS = auto()
    LIQUID = auto()
    SOLID = auto()
    FLUID = GAS | LIQUID


class Material:
    def __init__(self):
        self._name = None
        self._phase = None
        self._molecularWeight = None
        self._density = None
        self._viscosity = None
        self._conductivity = None
        self._specificHeat = None
        self._emissivity = None
        self._absorptionCoefficient = None
        self._sutherlandTemperature = None
        self._sutherlandCoefficient = None
        self._surfaceTension = None
        self._saturationPressure = None

    @property
    def name(self):
        return self._name

    @property
    def phase(self):
        return self._phase

    @property
    def molecularWeight(self):
        return self._molecularWeight

    @property
    def density(self):
        return self._density

    @property
    def viscosity(self):
        return self._viscosity

    @property
    def conductivity(self):
        return self._conductivity

    @property
    def specificHeat(self):
        return self._specificHeat

    @property
    def emissivity(self):
        return self._emissivity

    @property
    def absorptionCoefficient(self):
        return self._absorptionCoefficient

    @property
    def sutherlandTemperature(self):
        return self._sutherlandCoefficient

    @property
    def sutherlandCoefficient(self):
        return self._sutherlandCoefficient

    @property
    def surfaceTension(self):
        return self._surfaceTension

    @property
    def saturationPressure(self):
        return self._saturationPressure
