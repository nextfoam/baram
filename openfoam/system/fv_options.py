#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from coredb import coredb
from coredb.cell_zone_db import CellZoneDB
from openfoam.dictionary_file import DictionaryFile

logger = logging.getLogger(__name__)

class FvOptions(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.systemLocation(rname), 'fvOptions')

        self._rname = rname
        self._db = coredb.CoreDB()

    def build(self):
        if self._data is not None:
            return
        self._data = {}

        cellZones = self._db.getCellZones(self._rname)
        for czid, cname in cellZones:
            xpath = CellZoneDB.getXPath(czid)

            # Zone Type
            self._buildZoneType(cname, xpath)

            # Source Terms
            self._buildSourceTerms(cname, xpath + '/sourceTerms')

            # Fixed
            self._buildFixedValues(cname, xpath + '/fixedValues')

        return self

    # --------------------------------------------------------------------------
    # Zone Type
    # --------------------------------------------------------------------------
    def _buildZoneType(self, cname, xpath):
        zoneType = self._db.getValue(xpath + '/zoneType')

        if zoneType == 'porous':
            self._buildPorous(cname, xpath + '/porous')

        elif zoneType == 'actuatorDisk':
            self._buildActuatorDisk(cname, xpath + '/actuatorDisk')

        else:   # zoneType == 'None':
            pass

    # --------------------------------------------------------------------------
    def _buildPorous(self, cname, xpath):
        dictName = f'porosity_{cname}'
        explicitData = self._buildExplicit(xpath)

        self._data[dictName] = {
            'type': 'explicitPorositySource',
            'explicitPorositySourceCoeffs': explicitData
        }
        if cname == 'All':
            self._data[dictName]['explicitPorositySourceCoeffs']['selectionMode'] = 'all'
        else:
            self._data[dictName]['explicitPorositySourceCoeffs']['selectionMode'] = 'cellZone'
            self._data[dictName]['explicitPorositySourceCoeffs']['cellZone'] = 'porosity'

    def _buildExplicit(self, xpath):
        data = {}
        porosityModel = self._db.getValue(xpath + '/model')

        if porosityModel == 'darcyForchheimer':
            d = self._db.getVector(xpath + '/darcyForchheimer/viscousResistanceCoefficient')
            f = self._db.getVector(xpath + '/darcyForchheimer/inertialResistanceCoefficient')
            d1 = self._db.getVector(xpath + '/darcyForchheimer/direction1Vector')
            d2 = self._db.getVector(xpath + '/darcyForchheimer/direction2Vector')

            data = {
                'type': 'darcyForchheimer',
                'DarcyForchheimerCoeffs':{
                    'd': ('d', '[ 0 -2 0 0 0 0 0 ]', d),
                    'f': ('f', '[ 0 -1 0 0 0 0 0 ]', f),
                    'coordinateSystem': {
                        'type': 'cartesian',
                        'origin': '(0 0 0)',
                        'coordinateRotation': {
                            'type': 'axesRotation',
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
                    'C1': c1
                }
            }
        return data

    # --------------------------------------------------------------------------
    def _buildActuatorDisk(self, cname, xpath):
        dictName = f'actuationDiskSource_{cname}'
        diskDirection = self._db.getVector(xpath + '/diskDirection')
        powerCoefficient = self._db.getValue(xpath + '/powerCoefficient')
        thrustCoefficient = self._db.getValue(xpath + '/thrustCoefficient')
        diskArea = self._db.getValue(xpath + '/diskArea')
        upstreamPoint = self._db.getVector(xpath + '/upstreamPoint')

        self._data[dictName] = {
            'type': 'actuationDiskSource',
            'fields': '(U)',
            'diskDir': diskDirection,
            'Cp': powerCoefficient,
            'Ct': thrustCoefficient,
            'diskArea': diskArea,
            'upstreamPoint': upstreamPoint
        }
        if cname == 'All':
            self._data[dictName]['selectionMode'] = 'all'
        else:
            self._data[dictName]['selectionMode'] = 'cellZone'
            self._data[dictName]['cellZone'] = 'porosity'

    # --------------------------------------------------------------------------
    # Source Terms
    # --------------------------------------------------------------------------
    def _buildSourceTerms(self, cname, xpath):
        self._buildSourceFields(cname, xpath + '/mass', 'rho')
        self._buildSourceFields(cname, xpath + '/energy', 'h')

        modelsType = self._db.getValue('.//models/turbulenceModels/model')
        if modelsType == 'spalartAllmaras':
            self._buildSourceFields(cname, xpath + '/modifiedTurbulentViscosity', 'nuTilda')

        elif modelsType == 'k-epsilon':
            self._buildSourceFields(cname, xpath + '/turbulentKineticEnergy', 'k')
            self._buildSourceFields(cname, xpath + '/turbulentDissipationRate', 'epsilon')

        elif modelsType == 'k-omega':
            self._buildSourceFields(cname, xpath + '/turbulentKineticEnergy', 'k')
            self._buildSourceFields(cname, xpath + '/specificDissipationRate', 'omega')
        else:
            logger.debug('Error Model Type')

    # --------------------------------------------------------------------------
    def _buildSourceFields(self, cname, xpath, fieldType):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            dictName = f'scalarSource_{cname}_{fieldType}'
            volumeMode = self._buildVolumeMode(xpath)
            injectionRateSuSp = self._buildInjectionRateSuSp(xpath, fieldType)

            self._data[dictName] = {
                'type': 'scalarSemiImplicitSource',
                'duration': '1000.0',
                'volumeMode': volumeMode,
                'injectionRateSuSp': injectionRateSuSp
            }
            if cname == 'All':
                self._data[dictName]['selectionMode'] = 'all'
            else:
                self._data[dictName]['selectionMode'] = 'cellZone'
                self._data[dictName]['cellZone'] = 'porosity'

    def _buildVolumeMode(self, xpath):
        data = ''
        if self._db.getValue(xpath + '/unit') == 'valueForEntireCellZone':
            data = 'absolute'
        elif self._db.getValue(xpath + '/unit') == 'valuePerUnitVolume':
            data = 'specific'
        else:
            logger.debug('Error volumeMode')

        return data

    def _buildInjectionRateSuSp(self, xpath, fieldType) -> dict:
        data = {}

        if fieldType == 'nuTilda' or fieldType == 'k' \
                or fieldType == 'epsilon' or fieldType == 'omega':
            valueType = 'constant'
        else:   # 'rho' , 'h'
            valueType = self._db.getValue(xpath + '/specification')

        if valueType == 'constant':
            value = self._db.getValue(xpath + '/constant')
            data = {
                fieldType: {
                    'Su': value,
                    'Sp': '0.0'
                }
            }
        elif valueType == 'piecewiseLinear':
            t = self._db.getValue(xpath + '/piecewiseLinear/t').split()
            v = self._db.getValue(xpath + '/piecewiseLinear/v').split()
            value = [[t[i], v[i]] for i in range(len(t))]
            data = {
                fieldType: {
                    'Su': ('table', value),
                    'Sp': '0.0'
                }
            }
        elif valueType == 'polynomial':
            value = []
            v = self._db.getValue(xpath + '/polynomial').split()
            for i in range(len(v)):
                value.append([v[i], i])
            data = {
                fieldType: {
                    'Su': ('polynomial', value),
                    'Sp': '0.0'
                }
            }
        return data

    # --------------------------------------------------------------------------
    # Fixed Value
    # --------------------------------------------------------------------------
    def _buildFixedValues(self, cname, xpath):
        self._buildFixedVelocity(cname, xpath + '/velocity')
        self._buildFixedTemperature(cname, xpath + '/temperature')

        modelsType = self._db.getValue('.//models/turbulenceModels/model')
        if modelsType == 'spalartAllmaras':
            self._buildFixedFields(cname, xpath + '/modifiedTurbulentViscosity', 'nuTilda')

        elif modelsType == 'k-epsilon':
            self._buildFixedFields(cname, xpath + '/turbulentKineticEnergy', 'k')
            self._buildFixedFields(cname, xpath + '/turbulentDissipationRate', 'epsilon')

        elif modelsType == 'k-omega':
            self._buildFixedFields(cname, xpath + '/turbulentKineticEnergy', 'k')
            self._buildFixedFields(cname, xpath + '/specificDissipationRate', 'omega')

        else:
            logger.debug('Error Model Type')

    # --------------------------------------------------------------------------
    def _buildFixedVelocity(self, cname, xpath):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            dictName = f'fixedVelocity_{cname}'
            uBar = self._db.getVector(xpath + '/velocity')
            relaxation = self._db.getValue(xpath + '/relaxation')

            self._data[dictName] = {
                'type': 'meanVelocityForce',
                'active': 'yes',
                'fields': '(U)',
                'Ubar': uBar,
                'relaxation': relaxation
            }
            if cname == 'All':
                self._data[dictName]['selectionMode'] = 'all'
            else:
                self._data[dictName]['selectionMode'] = 'cellZone'
                self._data[dictName]['cellZone'] = 'porosity'

    def _buildFixedTemperature(self, cname, xpath):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            dictName = f'fixedTemperature_{cname}'
            temperature = self._db.getValue(xpath)

            self._data[dictName] = {
                'type': 'fixedTemperatureConstraint',
                'active': 'yes',
                'mode': 'uniform',
                'temperature': ('constant', temperature)
            }
            if cname == 'All':
                self._data[dictName]['selectionMode'] = 'all'
            else:
                self._data[dictName]['selectionMode'] = 'cellZone'
                self._data[dictName]['cellZone'] = 'porosity'

    def _buildFixedFields(self, cname, xpath, fieldType):
        if self._db.getAttribute(xpath, 'disabled') == 'false':
            dictName = f'fixedValue_{cname}_{fieldType}'
            fieldValues = self._db.getValue(xpath)

            self._data[dictName] = {
                'type': 'scalarFixedValueConstraint',
                'active': 'yes',
                'fieldValues': {
                    fieldType: fieldValues
                }
            }
            if cname == 'All':
                self._data[dictName]['selectionMode'] = 'all'
            else:
                self._data[dictName]['selectionMode'] = 'cellZone'
                self._data[dictName]['cellZone'] = 'porosity'
