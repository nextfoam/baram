#!/usr/bin/env python
# -*- coding: utf-8 -*-
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader, Region
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import MaterialType
from baramFlow.coredb.cell_zone_db import CellZoneDB

from baramFlow.openfoam.file_system import FileSystem


class SetFieldsDict(DictionaryFile):
    def __init__(self, region: Region):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(region.rname), 'setFieldsDict')

        self._region = region

    def build(self):
        if self._data is not None:
            return self

        defaultFields = []
        defaultFieldValues = []  # "defaultFieldValues" in "setFieldsDict"
        sections = []  # "regions" in "setFieldsDict"

        db = CoreDBReader()

        rname = self._region.rname
        sectionNames: [str] = db.getList(f'.//regions/region[name="{rname}"]/initialization/advanced/sections/section/name')
        if len(sectionNames) == 0:
            return self

        ivPath = f'.//regions/region[name="{rname}"]/initialization/initialValues'

        for name in sectionNames:
            sPath = f'.//regions/region[name="{rname}"]/initialization/advanced/sections/section[name="{name}"]'

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
                defaultPrimaryFraction = 1
                sectionPrimaryFraction = 1
                for mid in materials:
                    fieldName = 'alpha.' + MaterialDB.getName(mid)
                    fraction = db.getValue(sPath + f'/volumeFractions/volumeFraction[material="{mid}"]/fraction')
                    sectionPrimaryFraction -= float(fraction)
                    fieldValues.append(('volScalarFieldValue', fieldName, fraction))
                    if fieldName not in defaultFields:
                        defaultFields.append(fieldName)
                        defaultFraction = db.getValue(ivPath + f'/volumeFractions/volumeFraction[material="{mid}"]/fraction')
                        defaultPrimaryFraction -= float(defaultFraction)
                        defaultFieldValues.append(('volScalarFieldValue', fieldName, defaultFraction))

                fieldName = 'alpha.' + MaterialDB.getName(self._region.mid)
                if fieldName not in defaultFields:
                    defaultFields.append(fieldName)
                    defaultFieldValues.append(('volScalarFieldValue', fieldName, defaultPrimaryFraction))
                fieldValues.append(('volScalarFieldValue', fieldName, sectionPrimaryFraction))

            for scalarID, fieldName in db.getUserDefinedScalarsInRegion(rname):
                scalarXPath = f'{sPath}/userDefinedScalars/scalar[scalarID="{scalarID}"]/value'
                if db.getAttribute(scalarXPath, 'disabled') == 'false':
                    value = db.getValue(scalarXPath)
                    fieldValues.append(('volScalarFieldValue', fieldName, value))
                    if fieldName not in defaultFields:
                        defaultFields.append(fieldName)
                        defaultValue = db.getValue(ivPath + f'/userDefinedScalars/scalar[scalarID="{scalarID}"]/value')
                        defaultFieldValues.append(('volScalarFieldValue', fieldName, defaultValue))

            if ModelsDB.isSpeciesModelOn():
                mid = RegionDB.getMaterial(rname)
                if MaterialDB.getType(mid) == MaterialType.MIXTURE:
                    mixtureXPath = f'{sPath}/species/mixture[mid="{mid}"]'
                    if db.getAttribute(mixtureXPath, 'disabled') == 'false':
                        for specie, fieldName in MaterialDB.getSpecies(mid).items():
                            value = db.getValue(f'{mixtureXPath}/specie[mid="{specie}"]/value')
                            fieldValues.append(('volScalarFieldValue', fieldName, value))
                            if fieldName not in defaultFields:
                                defaultFields.append(fieldName)
                                defaultValue = db.getValue(ivPath + f'/species/mixture[mid="{mid}"]/specie[mid="{specie}"]/value')
                                defaultFieldValues.append(('volScalarFieldValue', fieldName, defaultValue))

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
