#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baram.coredb import coredb
from baram.coredb.material_db import MaterialDB
from baram.coredb.cell_zone_db import CellZoneDB

from baram.openfoam.file_system import FileSystem


class SetFieldsDict(DictionaryFile):
    def __init__(self, rname: str = ''):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(rname), 'setFieldsDict')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        defaultFields = []
        defaultFieldValues = []  # "defaultFieldValues" in "setFieldsDict"
        sections = []  # "regions" in "setFieldsDict"

        db = coredb.CoreDB()

        sectionNames: [str] = db.getList(f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section/name')
        if len(sectionNames) == 0:
            return self

        ivPath = f'.//regions/region[name="{self._rname}"]/initialization/initialValues'

        for name in sectionNames:
            sPath = f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{name}"]'

            fieldValues = []

            if db.getAttribute(sPath+'/velocity', 'disabled') == 'false':
                fieldValues.append(('volVectorFieldValue', 'U', db.getVector(sPath + '/velocity')))
                if 'U' not in defaultFields:
                    defaultFields.append('U')
                    defaultFieldValues.append(('volVectorFieldValue', 'U', db.getVector(ivPath + '/velocity')))

            if db.getAttribute(sPath+'/pressure', 'disabled') == 'false':
                fieldValues.append(('volScalarFieldValue', 'p', db.getValue(sPath + '/pressure')))
                if 'p' not in defaultFields:
                    defaultFields.append('p')
                    defaultFieldValues.append(('volScalarFieldValue', 'p', db.getValue(ivPath + '/pressure')))

            if db.getAttribute(sPath+'/temperature', 'disabled') == 'false':
                fieldValues.append(('volScalarFieldValue', 'T', db.getValue(sPath + '/temperature')))
                if 'T' not in defaultFields:
                    defaultFields.append('T')
                    defaultFieldValues.append(('volScalarFieldValue', 'T', db.getValue(ivPath + '/temperature')))

            if db.getAttribute(sPath+'/volumeFractions', 'disabled') == 'false':
                materials: [str] = db.getList(sPath + f'/volumeFractions/volumeFraction/material')
                for mid in materials:
                    fieldName = 'alpha.' + MaterialDB.getName(mid)
                    fraction = db.getValue(sPath + f'/volumeFractions/volumeFraction[material="{mid}"]/fraction')
                    fieldValues.append(('volScalarFieldValue', fieldName, fraction))
                    if fieldName not in defaultFields:
                        defaultFields.append(fieldName)
                        defaultFraction = db.getValue(ivPath + f'/volumeFractions/volumeFraction[material="{mid}"]/fraction')
                        defaultFieldValues.append(('volScalarFieldValue', fieldName, defaultFraction))

            if db.getValue(sPath + '/overrideBoundaryValue') == 'true':
                overrideBoundaryValue = True
            else:
                overrideBoundaryValue = False

            stype = db.getValue(sPath + '/type')
            if stype == 'hex':
                data = {
                    'box': (
                        db.getVector(sPath + '/point1'),
                        db.getVector(sPath + '/point2'),
                    ),
                    'fieldValues': fieldValues
                }
                sections.append(('boxToCell', data))
                if overrideBoundaryValue:
                    sections.append(('boxToFace', data))
            elif stype == 'cylinder':
                data = {
                    'point1': db.getVector(sPath + '/point1'),
                    'point2': db.getVector(sPath + '/point2'),
                    'radius': db.getValue(sPath + '/radius'),
                    'fieldValues': fieldValues
                }
                sections.append(('cylinderToCell', data))
                if overrideBoundaryValue:
                    sections.append(('cylinderToFace', data))
            elif stype == 'sphere':
                data = {
                    'origin': db.getVector(sPath + '/point1'),
                    'radius': db.getValue(sPath + '/radius'),
                    'fieldValues': fieldValues
                }
                sections.append(('sphereToCell', data))
                if overrideBoundaryValue:
                    sections.append(('sphereToFace', data))
            elif stype == 'cellZone':
                czid = db.getValue(sPath + '/cellZone')
                data = {
                    'zone': CellZoneDB.getCellZoneName(czid),
                    'fieldValues': fieldValues
                }
                sections.append(('zoneToCell', data))
                if overrideBoundaryValue:
                    sections.append(('zoneToFace', data))

        self._data = {
            'defaultFieldValues': defaultFieldValues,
            'regions': sections
        }

        return self
