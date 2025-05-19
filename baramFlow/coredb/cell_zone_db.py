# -*- coding: utf-8 -*-

from enum import Enum

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import IMaterialObserver
from baramFlow.coredb.region_db import IRegionMaterialObserver, RegionDB, REGION_XPATH, CELL_ZONE_NAME_FOR_REGION
from baramFlow.coredb.scalar_model_db import IUserDefinedScalarObserver
from baramFlow.view.widgets.multi_selector_dialog import SelectorItem


CELL_ZONE_CONDITION_XPATH = REGION_XPATH + '/cellZones/cellZone'


class ZoneType(Enum):
    NONE = 'none'
    MRF = 'mrf'
    POROUS = 'porous'
    SLIDING_MESH = 'slidingMesh'
    ACTUATOR_DISK = 'actuatorDisk'


class PorousZoneModel(Enum):
    DARCY_FORCHHEIMER = 'darcyForchheimer'
    POWER_LAW = 'powerLaw'


class SpecificationMethod(Enum):
    VALUE_PER_UNIT_VOLUME = 'valuePerUnitVolume'
    VALUE_FOR_ENTIRE_CELL_ZONE = 'valueForEntireCellZone'


class TemporalProfileType(Enum):
    CONSTANT = 'constant'
    PIECEWISE_LINEAR = 'piecewiseLinear'
    POLYNOMIAL = 'polynomial'


class CellZoneDB:
    CELL_ZONE_CONDITIONS_XPATH = '/regions/region/cellZones'

    _cellzones = None

    @classmethod
    def getXPath(cls, czid):
        return f'{CELL_ZONE_CONDITION_XPATH}[@czid="{czid}"]'

    @classmethod
    def getCellZoneName(cls, czid):
        return coredb.CoreDB().getValue(cls.getXPath(czid) + '/name')

    @classmethod
    def getCellZoneRegion(cls, czid):
        return coredb.CoreDB().getValue(cls.getXPath(czid) + '/../../name')

    @classmethod
    def getCellZoneText(cls, czid):
        rname = cls.getCellZoneRegion(czid)
        r = '' if rname == '' else rname + ':'
        return f'{r}{cls.getCellZoneName(czid)}' if czid else ''

    @classmethod
    def getCellZoneType(cls, czid):
        return ZoneType(coredb.CoreDB().getValue(cls.getXPath(czid) + '/zoneType'))

    @classmethod
    def isRegion(cls, czname):
        return czname == CELL_ZONE_NAME_FOR_REGION

    @classmethod
    def getCellZoneSelectorItems(cls):
        db = coredb.CoreDB()

        if not cls._cellzones:
            cls._cellzones = []

            for rname in db.getRegions():
                r = '' if rname == '' else rname + ':'
                for czid, czname in db.getCellZones(rname):
                    # if czname != cls.NAME_FOR_ALL:
                    cls._cellzones.append(SelectorItem(f'{r}{czname}', czname, str(czid)))

        return cls._cellzones


def getCellZoneElements(rname=None):
    return coredb.CoreDB().getElements(f'{RegionDB.getXPath(rname)}/cellZones/cellZone')


def _addMaterialSourceTerm(parent, mid):
    if xml.getElement(parent, f'materialSource[material="{mid}"]') is None:
        parent.append(
            xml.createElement('<materialSource xmlns="http://www.baramcfd.org/baram" disabled="true">'
                              f'  <material>{mid}</material>'
                              '   <unit>valueForEntireCellZone</unit>'
                              '    <specification>constant</specification>'
                              '    <constant>0</constant>'
                              '    <piecewiseLinear>'
                              '        <t>0</t>'
                              '        <v>0</v>'
                              '    </piecewiseLinear>'
                              '    <polynomial>0</polynomial>'
                              '</materialSource>')
        )


class MaterialObserver(IMaterialObserver):
    def specieAdded(self, db, mid, mixtureID):
        for cellZone in db.getElements(f'{REGION_XPATH}[material="{mixtureID}"]/cellZones/cellZone'):
            for sourceTerms in xml.getElements(cellZone, f'sourceTerms/materials'):
                _addMaterialSourceTerm(sourceTerms, mid)

            for mixture in xml.getElements(cellZone, f'fixedValues/species/mixture[mid="{mixtureID}"]'):
                mixture.append(xml.createElement('<specie xmlns="http://www.baramcfd.org/baram">'
                                                 f' <mid>{mid}</mid><value disabled="true">0</value>'
                                                 '</specie>'))

    def specieRemoving(self, db, mid, primarySpecie):
        for cellZone in db.getElements(CELL_ZONE_CONDITION_XPATH):
            for sourceTerm in xml.getElements(cellZone, f'sourceTerms/materials/materialSource[material="{mid}"]'):
                sourceTerm.getparent().remove(sourceTerm)

            for specie in xml.getElements(cellZone, f'fixedValues/species/mixture/specie[mid="{mid}"]'):
                specie.getparent().remove(specie)


class RegionMaterialObserver(IRegionMaterialObserver):
    def materialsUpdating(self, db, rname, primary, secondaries, species):
        fixedValuesSpeciesXML = ''
        for mid in species:
            fixedValuesSpeciesXML += f'<specie><mid>{mid}</mid><value disabled="true">0</value></specie>'

        fixedValuesSpeciesXML = f'''<mixture xmlns="http://www.baramcfd.org/baram">
                                        <mid>{primary}</mid>{fixedValuesSpeciesXML}
                                    </mixture>'''

        for cellZone in getCellZoneElements(rname):
            materialSourceTerms = xml.getElement(cellZone, f'sourceTerms/materials')
            for sourceTerm in xml.getElements(materialSourceTerms, f'materialSource'):
                sourceTermMaterial = xml.getText(sourceTerm, 'material')
                if sourceTermMaterial not in secondaries and sourceTermMaterial not in species:
                    sourceTerm.getparent().remove(sourceTerm)

            for mid in secondaries:
                _addMaterialSourceTerm(materialSourceTerms, mid)

            for mid in species:
                _addMaterialSourceTerm(materialSourceTerms, mid)

            fixedValuesSpecies = xml.getElement(cellZone, 'fixedValues/species')
            fixedValuesSpecies.clear()

            if species:
                fixedValuesSpecies.append(xml.createElement(fixedValuesSpeciesXML))


class ScalarObserver(IUserDefinedScalarObserver):
    def scalarAdded(self, db, scalarID):
        sourceTermXML = f'''<scalarSource disabled="true" xmlns="http://www.baramcfd.org/baram">
                                <scalarID>{scalarID}</scalarID>
                                <unit>valueForEntireCellZone</unit>
                                <specification>constant</specification>
                                <constant>0</constant>
                                <piecewiseLinear><t>0</t><v>0</v></piecewiseLinear>
                                <polynomial>0</polynomial>
                             </scalarSource>'''
        fixedValueXML = f'''<scalar xmlns="http://www.baramcfd.org/baram">
                                <scalarID>{scalarID}</scalarID>
                                <value disabled="true">0</value>
                            </scalar>'''

        for cellZone in db.getElements(CELL_ZONE_CONDITION_XPATH):
            scalarSourceTerms = xml.getElement(cellZone, 'sourceTerms/userDefinedScalars')
            scalarSourceTerms.append(xml.createElement(sourceTermXML))

            scalarFixedValues = xml.getElement(cellZone, 'fixedValues/userDefinedScalars')
            scalarFixedValues.append(xml.createElement(fixedValueXML))

    def scalarRemoving(self, db, scalarID):
        for cellZone in db.getElements(CELL_ZONE_CONDITION_XPATH):
            xml.removeElement(xml.getElement(cellZone, 'sourceTerms/userDefinedScalars'),
                              f'scalarSource[scalarID="{scalarID}"]')
            xml.removeElement(xml.getElement(cellZone, 'fixedValues/userDefinedScalars'),
                              f'scalar[scalarID="{scalarID}"]')
