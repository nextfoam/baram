#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from baramFlow.base.base import Vector
from baramFlow.base.boundary.boundary_data import BoundaryData
from baramFlow.base.cell_zone.cell_zone import CellZoneData
from baramFlow.coredb.libdb import E, nsmap
from baramFlow.coredb.region_db import CELL_ZONE_NAME_FOR_REGION

CELL_ZONE_PATH = 'configurations/cell_zone.xml'


@dataclass
class BoundaryModel:
    boundary: BoundaryData
    startFace: int = 0
    rname: str = ''
    zoneAverageDirection: list = None

    @property
    def bcid(self):
        return self.boundary.bcid

    @property
    def name(self):
        return self.boundary.name

    @property
    def bctype(self):
        return self.boundary.bctype

    @property
    def scopedName(self):
        return self.boundary.name if self.rname == '' else f'{self.rname}:{self.boundary.name}'

    def setID(self, bcid: str):
        assert self.boundary.bcid is None
        self.boundary.bcid = bcid

    def toElement(self):
        return self.boundary.toElement()



@dataclass
class CellZoneModel:
    configurations: CellZoneData
    rname: str = ''

    @property
    def czid(self):
        return self.configurations.czid

    @property
    def name(self):
        return self.configurations.name

    @property
    def scopedName(self):
        return self.configurations.name if self.rname == '' else f'{self.rname}:{self.configurations.name}'

    def setID(self, czid: str):
        assert self.configurations.czid == ''
        self.configurations.czid = czid

    def isRegion(self):
        return self.configurations.isRegion()

    def toElement(self):
        return self.configurations.toElement()


@dataclass
class RegionInitialValues:
    velocity: Vector
    pressure: str
    temperature: str
    scaleOfVelocity: str
    turbulentIntensity: str
    turbulentViscosity: str
    intermittency: str
    momentumThicknessRe: str
    # volumeFractions: list = None
    # userDefinedScalars: list = None
    # species: list = None

    @classmethod
    def default(cls):
        return RegionInitialValues(velocity=Vector.zero(),
                                   pressure='0',
                                   temperature='300',
                                   scaleOfVelocity='1',
                                   turbulentIntensity='1',
                                   turbulentViscosity='10',
                                   intermittency='1',
                                   momentumThicknessRe='200')

    def toElement(self):
        return E('initialValues',
                  self.velocity.toElement('velocity'),
                  E('pressure', self.pressure),
                  E('temperature', self.temperature),
                  E('scaleOfVelocity', self.scaleOfVelocity),
                  E('turbulentIntensity', self.turbulentIntensity),
                  E('turbulentViscosity', self.turbulentViscosity),
                  E('intermittency', self.intermittency),
                  E('momentumThicknessRe', self.momentumThicknessRe),
                  E('volumeFractions'),
                  E('userDefinedScalars'),
                  E('species'))

    @staticmethod
    def fromElement(e):
        return RegionInitialValues(velocity=Vector.fromElement(e.find('velocity', namespaces=nsmap)),
                                   pressure=e.find('pressure', namespaces=nsmap).text,
                                   temperature=e.find('temperature', namespaces=nsmap).text,
                                   scaleOfVelocity=e.find('scaleOfVelocity', namespaces=nsmap).text,
                                   turbulentIntensity=e.find('turbulentIntensity', namespaces=nsmap).text,
                                   turbulentViscosity=e.find('turbulentViscosity', namespaces=nsmap).text,
                                   intermittency=e.find('intermittency', namespaces=nsmap).text,
                                   momentumThicknessRe=e.find('momentumThicknessRe', namespaces=nsmap).text)


@dataclass
class RegionInitialization:
    initialValues: RegionInitialValues = field(default_factory=RegionInitialValues.default)

    def toElement(self):
        return E('initialization',
                    self.initialValues.toElement(),
                    E('advanced', E('sections')))

    @staticmethod
    def fromElement(e):
        return RegionInitialization(
            initialValues=RegionInitialValues.fromElement(e.find('initialValues', namespaces=nsmap)))



@dataclass
class RegionModel:
    name: str
    material: str
    boundaries: list[BoundaryModel] = field(default_factory=list)
    cellZones: list[CellZoneModel] = field(default_factory=list)
    initialization: RegionInitialization    = field(default_factory=RegionInitialization)

    def addBoundary(self, boundary: BoundaryModel):
        self.boundaries.append(boundary)

    def addCellZone(self, cellZone: CellZoneModel):
        self.cellZones.append(cellZone)

    def getBoundaryNames(self):
        return [model.name for model in self.boundaries]

    def getCellZoneNames(self, includeEntireZone=True):
        if includeEntireZone:
            return [model.name for model in self.cellZones]
        else:
            return [model.name for model in self.cellZones if model.name != CELL_ZONE_NAME_FOR_REGION]

    def sortBoundaries(self):
        self.boundaries.sort(key=lambda b: b.startFace)

    def toElement(self):
        element = E('region',
                      E('name', self.name),
                      E('material', self.material),
                      E('secondaryMaterials'),
                      E('phaseInteractions',  E('surfaceTensions'),
                          E('massTransfers',
                              E('massTransfer',
                                  E('from', '0'),
                                  E('to', '0'),
                                  E('mechanism', 'cavitation'),
                                  E('cavitation',
                                  E('model', 'none'),
                                  E('vaporizationPressure', '2300'),
                                  E('schnerrSauer',
                                      E('evaporationCoefficient', '1'),
                                      E('condensationCoefficient', '1'),
                                      E('bubbleDiameter', '2.0e-06'),
                                      E('bubbleNumberDensity', '1.6e+13')),
                                  E('kunz',
                                      E('evaporationCoefficient', '1000'),
                                      E('condensationCoefficient', '1000'),
                                      E('meanFlowTimeScale', '0.005'),
                                      E('freeStreamVelocity', '20.0')),
                                  E('merkle',
                                      E('evaporationCoefficient', '1e-3'),
                                      E('condensationCoefficient', '80'),
                                      E('meanFlowTimeScale', '0.005'),
                                      E('freeStreamVelocity', '20.0')),
                                  E('zwartGerberBelamri',
                                      E('evaporationCoefficient', '1'),
                                      E('condensationCoefficient', '1'),
                                      E('bubbleDiameter', '2e-6'),
                                      E('nucleationSiteVolumeFraction', '1e-3')))))),
                      E('cellZones'),
                      E('boundaryConditions'),
                      self.initialization.toElement())

        boundaryConditions = element.find('boundaryConditions', namespaces=nsmap)
        for model in self.boundaries:
            boundaryConditions.append(model.toElement())

        cellZones = element.find('cellZones', namespaces=nsmap)
        for model in self.cellZones:
            cellZones.append(model.toElement())

        return element

    @staticmethod
    def fromElement(e):
        rname = e.find('name', namespaces=nsmap).text
        if rname is None:
            rname = ''

        boundaries = []
        for b in e.findall('boundaryConditions/boundaryCondition', namespaces=nsmap):
            boundaries.append(BoundaryModel(boundary=BoundaryData.fromElement(b),
                                            rname=rname))

        cellZones = []
        for c in e.findall('cellZones/cellZone', namespaces=nsmap):
            cellZones.append(CellZoneModel(configurations=CellZoneData.fromElement(c),
                                           rname=rname))

        return RegionModel(
            name=rname,
            material=e.find('material', namespaces=nsmap).text,
            boundaries=boundaries,
            cellZones=cellZones,
            initialization=RegionInitialization.fromElement(e.find('initialization', namespaces=nsmap)))
