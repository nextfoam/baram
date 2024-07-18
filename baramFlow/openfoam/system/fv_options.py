#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from baramFlow.coredb.region_db import RegionDB
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.material_db import MaterialDB, MaterialType
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.openfoam.file_system import FileSystem

logger = logging.getLogger(__name__)


def generateSourceTermField(czname, xpath, fieldType):
    volumeMode = _generateVolumeMode(xpath)
    injectionRate = _generateInjectionRate(xpath, fieldType)

    data = {
        'type': 'scalarSemiImplicitSource',
        'volumeMode': volumeMode,
        'sources': injectionRate
    }
    if czname == 'All':
        data['selectionMode'] = 'all'
    else:
        data['selectionMode'] = 'cellZone'
        data['cellZone'] = czname

    return data


def generateFixedValueField(czname, xpath, fieldType):
    db = CoreDBReader()

    data = {
        'type': 'scalarFixedValueConstraint',
        'active': 'yes',
        'fieldValues': {
            fieldType: db.getValue(xpath)
        }
    }
    if czname == 'All':
        data['selectionMode'] = 'all'
    else:
        data['selectionMode'] = 'cellZone'
        data['cellZone'] = czname

    return data


def _generateVolumeMode(xpath):
    db = CoreDBReader()

    unitValue = db.getValue(xpath + '/unit')

    if unitValue == 'valueForEntireCellZone':
        data = 'absolute'
    elif unitValue == 'valuePerUnitVolume':
        data = 'specific'
    else:
        data = 'none'
        raise Exception(f'unitValue is {unitValue}')

    return data


def _generateInjectionRate(xpath, fieldType) -> dict:
    db = CoreDBReader()

    data = {}
    if fieldType in ['nuTilda', 'k', 'epsilon', 'omega']:
        valueType = 'constant'
    else:   # 'rho', 'h'
        valueType = db.getValue(xpath + '/specification')

    if valueType == 'constant':
        value = db.getValue(xpath + '/constant')
        data = {
            fieldType: [value, '0.0']
        }
    elif valueType == 'piecewiseLinear':
        t = db.getValue(xpath + '/piecewiseLinear/t').split()
        v = db.getValue(xpath + '/piecewiseLinear/v').split()
        value = [[t[i], v[i]] for i in range(len(t))]
        data = {
            fieldType: {
                'explicit': ('table', value),
                'implicit': 'none'
            }
        }
    elif valueType == 'polynomial':
        value = []
        v = db.getValue(xpath + '/polynomial').split()
        for i in range(len(v)):
            value.append([v[i], i])
        data = {
            fieldType: {
                'explicit': ('polynomial', value),
                'implicit': 'none'
            }
        }
    return data


class FvOptions(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(rname), 'fvOptions')

        self._rname = rname
        self._db = CoreDBReader()

    def build(self):
        if self._data is not None:
            return self

        self._data = {}

        if ModelsDB.isEnergyModelOn():
            self._data = {
                'limitT': {
                    'type': 'limitTemperature',
                    'active': 'yes',
                    'selectionMode': 'all',
                    'min': self._db.getValue('.//numericalConditions/advanced/limits/minimumStaticTemperature'),
                    'max': self._db.getValue('.//numericalConditions/advanced/limits/maximumStaticTemperature')
                }
            }

        cellZones = self._db.getCellZones(self._rname)
        for czid, czname in cellZones:
            xpath = CellZoneDB.getXPath(czid)

            self._generateZoneType(czname, xpath)
            self._generateSourceTerms(czname, xpath + '/sourceTerms')
            self._generateFixedValues(czname, xpath + '/fixedValues')

        return self

    def _generateZoneType(self, czname, xpath):
        zoneType = self._db.getValue(xpath + '/zoneType')

        if zoneType == 'porous':
            self._generatePorous(czname, xpath + '/porous')

        elif zoneType == 'actuatorDisk':
            self._generateActuatorDisk(czname, xpath + '/actuatorDisk')

        else:   # 'none', 'mrf', 'slidingMesh'
            pass

    def _generatePorous(self, czname, xpath):
        dictName = f'porosity_{czname}'
        explicitData = self._generateExplicit(xpath)

        self._data[dictName] = {
            'type': 'explicitPorositySource',
            'explicitPorositySourceCoeffs': explicitData
        }
        if czname == 'All':
            self._data[dictName]['explicitPorositySourceCoeffs']['selectionMode'] = 'all'
        else:
            self._data[dictName]['explicitPorositySourceCoeffs']['selectionMode'] = 'cellZone'
            self._data[dictName]['explicitPorositySourceCoeffs']['cellZone'] = czname

    def _generateExplicit(self, xpath):
        data = {}
        porosityModel = self._db.getValue(xpath + '/model')

        if porosityModel == 'darcyForchheimer':
            d = self._db.getVector(xpath + '/darcyForchheimer/viscousResistanceCoefficient')
            f = self._db.getVector(xpath + '/darcyForchheimer/inertialResistanceCoefficient')
            d1 = self._db.getVector(xpath + '/darcyForchheimer/direction1Vector')
            d2 = self._db.getVector(xpath + '/darcyForchheimer/direction2Vector')

            data = {
                'type': 'DarcyForchheimer',
                'DarcyForchheimerCoeffs': {
                    'd': ('d', '[ 0 -2 0 0 0 0 0 ]', d),
                    'f': ('f', '[ 0 -1 0 0 0 0 0 ]', f),
                    'coordinateSystem': {
                        'type': 'cartesian',
                        'origin': '(0 0 0)',
                        'rotation': {
                            'type': 'axes',
                            'e1': d1,
                            'e2': d2
                        }
                    }
                }
            }
        elif porosityModel == 'powerLaw':
            c0 = self._db.getValue(xpath + '/powerLaw/c0')
            c1 = self._db.getValue(xpath + '/powerLaw/c1')

            data = {
                'type': 'powerLaw',
                'powerLawCoeffs': {
                    'C0': c0,
                    'C1': c1,
                    'coordinateSystem': {
                        'type': 'cartesian',
                        'origin': '(0 0 0)',
                        'rotation': {
                            'type': 'axesRotation',
                            'e1': [1, 0, 0],
                            'e2': [0, 1, 0]
                        }
                    }
                }
            }
        return data

    def _generateActuatorDisk(self, czname, xpath):
        dictName = f'actuationDiskSource_{czname}'
        diskDirection = self._db.getVector(xpath + '/diskDirection')
        powerCoefficient = self._db.getValue(xpath + '/powerCoefficient')
        thrustCoefficient = self._db.getValue(xpath + '/thrustCoefficient')
        diskArea = self._db.getValue(xpath + '/diskArea')
        forceComputation = self._db.getValue(xpath + '/forceComputation')

        self._data[dictName] = {
            'type': 'actuationDiskSource',
            'fields': '(U)',
            'diskDir': diskDirection,
            'Cp': powerCoefficient,
            'Ct': thrustCoefficient,
            'diskArea': diskArea,
            'monitorMethod': 'points',
            'monitorCoeffs': {
                'points' : [self._db.getVector(xpath + '/upstreamPoint')]
            },
            'variant': forceComputation
        }
        if czname == 'All':
            self._data[dictName]['selectionMode'] = 'all'
        else:
            self._data[dictName]['selectionMode'] = 'cellZone'
            self._data[dictName]['cellZone'] = czname

    def _generateSourceTerms(self, czname, xpath):
        if ModelsDB.isMultiphaseModelOn() or ModelsDB.isSpeciesModelOn():
            materials: [str] = self._db.getList(xpath+'/materials/materialSource/material')
            for mid in materials:
                name = MaterialDB.getName(mid)
                self._generateSourceFields(czname, xpath + f'/materials/materialSource[material="{mid}"]', f'alpha.{name}')
        else:
            self._generateSourceFields(czname, xpath + '/mass', 'rho')

        self._generateSourceFields(czname, xpath + '/energy', 'h')

        modelsType = self._db.getValue('.//models/turbulenceModels/model')
        if modelsType == 'spalartAllmaras':
            self._generateSourceFields(czname, xpath + '/modifiedTurbulentViscosity', 'nuTilda')

        elif modelsType == 'k-epsilon':
            self._generateSourceFields(czname, xpath + '/turbulentKineticEnergy', 'k')
            self._generateSourceFields(czname, xpath + '/turbulentDissipationRate', 'epsilon')

        elif modelsType == 'k-omega':
            self._generateSourceFields(czname, xpath + '/turbulentKineticEnergy', 'k')
            self._generateSourceFields(czname, xpath + '/specificDissipationRate', 'omega')
        else:
            logger.debug('Error Model Type')

    def _generateSourceFields(self, czname, xpath, fieldType):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            self._data[f'scalarSource_{czname}_{fieldType}'] = generateSourceTermField(czname, xpath, fieldType)

    def _generateFixedValues(self, czname, xpath):
        self._generateFixedVelocity(czname, xpath + '/velocity')
        self._generateFixedTemperature(czname, xpath + '/temperature')

        modelsType = self._db.getValue('.//models/turbulenceModels/model')
        if modelsType == 'spalartAllmaras':
            self._generateFixedFields(czname, xpath + '/modifiedTurbulentViscosity', 'nuTilda')

        elif modelsType == 'k-epsilon':
            self._generateFixedFields(czname, xpath + '/turbulentKineticEnergy', 'k')
            self._generateFixedFields(czname, xpath + '/turbulentDissipationRate', 'epsilon')

        elif modelsType == 'k-omega':
            self._generateFixedFields(czname, xpath + '/turbulentKineticEnergy', 'k')
            self._generateFixedFields(czname, xpath + '/specificDissipationRate', 'omega')
        else:
            logger.debug('Error Model Type')

        if ModelsDB.isSpeciesModelOn():
            material = RegionDB.getMaterial(self._rname)
            if MaterialDB.getType(material) == MaterialType.MIXTURE:
                for mid, specie in MaterialDB.getSpecies(material).items():
                    self._generateFixedFields(
                        czname, f'{xpath}/species/mixture[mid="{material}"]/specie[mid="{mid}"]/value', specie)

    def _generateFixedVelocity(self, czname, xpath):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            dictName = f'fixedVelocity_{czname}'
            uBar = self._db.getVector(xpath + '/velocity')
            relaxation = self._db.getValue(xpath + '/relaxation')

            self._data[dictName] = {
                'type': 'meanVelocityForce',
                'active': 'yes',
                'fields': '(U)',
                'Ubar': uBar,
                'relaxation': relaxation
            }
            if czname == 'All':
                self._data[dictName]['selectionMode'] = 'all'
            else:
                self._data[dictName]['selectionMode'] = 'cellZone'
                self._data[dictName]['cellZone'] = czname

    def _generateFixedTemperature(self, czname, xpath):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            dictName = f'fixedTemperature_{czname}'
            temperature = self._db.getValue(xpath)

            self._data[dictName] = {
                'type': 'fixedTemperatureConstraint',
                'active': 'yes',
                'mode': 'uniform',
                'temperature': ('constant', temperature)
            }
            if czname == 'All':
                self._data[dictName]['selectionMode'] = 'all'
            else:
                self._data[dictName]['selectionMode'] = 'cellZone'
                self._data[dictName]['cellZone'] = czname

    def _generateFixedFields(self, czname, xpath, fieldType):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            self._data[f'fixedValue_{czname}_{fieldType}'] = generateFixedValueField(czname, xpath, fieldType)
