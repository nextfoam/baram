#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.material_db import MaterialDB
from coredb.cell_zone_db import CellZoneDB

from openfoam.dictionary_file import DictionaryFile


class SetFieldsDict(DictionaryFile):
    def __init__(self, rname: str = ''):
        super().__init__(self.systemLocation(rname), 'setFieldsDict')

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
                overrideBoundaryValue = True

            stype = db.getValue(sPath + '/type')
            if stype == 'hex':
                if overrideBoundaryValue:
                    typeKey = '"(boxToCell|boxToFace)"'
                else:
                    typeKey = 'boxToCell'
                sections.append((
                    typeKey, {
                        'box': (
                            db.getVector(sPath + '/point1'),
                            db.getVector(sPath + '/point2'),
                        ),
                        'fieldValues': fieldValues
                    }
                ))
            elif stype == 'cylinder':
                if overrideBoundaryValue:
                    typeKey = '"(cylinderToCell|cylinderToFace)"'
                else:
                    typeKey = 'cylinderToCell'
                sections.append((
                    typeKey, {
                        'point1': db.getVector(sPath + '/point1'),
                        'point2': db.getVector(sPath + '/point2'),
                        'radius': db.getValue(sPath + '/radius'),
                        'fieldValues': fieldValues
                    }
                ))
            elif stype == 'sphere':
                if overrideBoundaryValue:
                    typeKey = '"(sphereToCell|sphereToFace)"'
                else:
                    typeKey = 'sphereToCell'
                sections.append((
                    typeKey, {
                        'origin': db.getVector(sPath + '/point1'),
                        'radius': db.getValue(sPath + '/radius'),
                        'fieldValues': fieldValues
                    }
                ))
            elif stype == 'cellZone':
                if overrideBoundaryValue:
                    typeKey = '"(zoneToCell|zoneToFace)"'
                else:
                    typeKey = 'zoneToCell'
                czid = db.getValue(sPath + '/cellZone')
                sections.append((
                    typeKey, {
                        'zone': CellZoneDB.getCellZoneName(czid),
                        'fieldValues': fieldValues
                    }
                ))

        self._data = {
            'defaultFieldValues': defaultFieldValues,
            'regions': sections
        }

        return self
