#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .material import Material, Phase


class MaterialDB:
    _instance = None

    def __init__(self):
        self._db = {}
        self._list = {}

        self._loadDB()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = MaterialDB()

        return cls._instance

    def _loadDB(self):
        self._appendDB('Air', Phase.GAS,
                       '28.966', '1.225', '1.79E-05', '0.0245', '1006', None, '0', '110.4', '1.46E-06')
        self._appendDB('O2', Phase.GAS,
                       '31.9988', '1.353', '2.00E-05', '0.0256', '918.3', None, '0', '139', '1.75E-06')
        self._appendDB('N2', Phase.GAS,
                       '28.0134', '1.185', '1.73E-05', '0.0251', '1041.3', None, '0', '107', '1.40E-06')
        self._appendDB('H2O', Phase.GAS,
                       '18.0153', '0.588', '1.22E-05', '0.0246', '2080', None, '0', '1064', '2.42E-06')
        self._appendDB('CO2', Phase.GAS,
                       '44.01', '1.861', '1.44E-05', '0.0159', '841.25', None, '0', '222', '1.50E-06')
        self._appendDB('H2', Phase.GAS,
                       '2.01588', '0.085', '8.69E-06', '0.181', '14268', None, '0', '97', '6.90E-06')
        self._appendDB('He', Phase.GAS,
                       '4.002602', '0.169', '1.94E-05', '0.152', '5193.2', None, '0', '99', '2.59E-05')
        self._appendDB('Ar', Phase.GAS,
                       '39.948', '1.69', '2.20E-05', '0.0172', '521.66', None, '0', '114', '1.82E-06')
        self._appendDB('CO', Phase.GAS,
                       '28.0106', '1.185', '1.73E-05', '0.0242', '1042', None, '0', '136', '1.50E-06')
        self._appendDB('CH4', Phase.GAS,
                       '16.043', '0.679', '1.08E-05', '0.0326', '2210', None, '0', '184', '1.04E-06')
        self._appendDB('Water', Phase.LIQUID,
                       '18.0153', '999.1', '1.14E-03', '0.5888', '4188.5', None, None, None, None, '0.07', '2300')
        self._appendDB('Steel', Phase.SOLID, None, '7850', None, '24.3', '450', '0.066')
        self._appendDB('Concrete', Phase.SOLID, None, '3000', None, '0.6', '1900', '0')
        self._appendDB('Aluminum', Phase.SOLID, None, '2707', None, '204', '896', '0.039')
        self._appendDB('Copper', Phase.SOLID, None, '8954', None, '386', '383.1', '0.023')

    def _appendDB(
            self, name, phase, molecularWeight, density, viscosity, conductivity, specificHeat, emissivity,
            absorptionCoefficient=None, sutherlandTemperature=None, sutherlandCoefficient=None,
            surfaceTension=None, saturationPressure=None):
        material = Material()
        material._name = name
        material._phase = phase
        material._molecularWeight = molecularWeight
        material._density = density
        material._viscosity = viscosity
        material._conductivity = conductivity
        material._specificHeat = specificHeat
        material._emissivity = emissivity
        material._absorptionCoefficient = absorptionCoefficient
        material._sutherlandTemperature = sutherlandTemperature
        material._sutherlandCoefficient = sutherlandCoefficient
        material._surfaceTension = surfaceTension
        material._saturationPressure = saturationPressure

        self._db[name] = material
        self._list[name] = name + " (" + phase.name + ")"

    def getMaterial(self, name):
        return self._db[name]

    def materialList(self):
        return self._list
