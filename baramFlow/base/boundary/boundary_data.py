#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID

from lxml import etree

from resources import resource

from baramFlow.base.base import UUID_ZERO
from baramFlow.base.boundary.boundary import SpecieRatios, PatchInteraction, userDefinedScalarsFromElement
from baramFlow.base.boundary.temperature import BoundaryTemperature
from baramFlow.base.boundary.velocity_inlet import VelocityInlet
from baramFlow.base.boundary.wall import Wall
from baramFlow.coredb.boundary_db import BoundaryType, GeometricalType
from baramFlow.coredb.libdb import nsmap


BOUNDARY_CONDITION_ELEMENT_PATH = 'configurations/boundary_condition.xml'


@dataclass
class BoundaryData:
    bcid: str                               = None

    name: str                               = None
    geometricalType: GeometricalType        = GeometricalType.PATCH
    bctype: BoundaryType                    = BoundaryType.WALL

    velocityInlet: VelocityInlet            = field(default_factory=VelocityInlet)
    # flowRateInlet: FlowRateInlet
    # flowRateOutlet: FlowRateOutlet
    # pressureInlet: PressureInlet
    # pressureOutlet: PressureOutlet
    # openChannelInlet: OpenChannelInlet
    # openChannelOutlet: OpenChannelOutlet
    # freeStream: FreeStream
    # farFieldRiemann: FarFieldRiemann
    # subsonicInlet: SubsonicInlet
    # subsonicOutflow: SubsonicOutflow
    # supersonicInflow: SupersonicInflow
    wall: Wall                              = field(default_factory=Wall)
    # thermoCoupledWall: ThermoCoupledWall
    # interface: Interface
    # porousJump: PorousJump

    # turbulence: BoundaryTurbulence
    temperature: BoundaryTemperature        = field(default_factory=BoundaryTemperature)
    coupledBoundary: str                    = '0'
    volumeFractions: list                   = None
    userDefinedScalars: list                = None
    species: SpecieRatios                   = None
    pressure: str                           = '0'
    fanCurveName: UUID                      = UUID_ZERO
    patchInteraction: PatchInteraction      = field(default_factory=PatchInteraction)

    def toElement(self):
        with open(resource.file(BOUNDARY_CONDITION_ELEMENT_PATH), 'rb') as file:
            xml = file.read()

        element = etree.fromstring(xml)
        element.set('bcid', self.bcid)
        element.find('name', namespaces=nsmap).text = self.name
        element.find('geometricalType', namespaces=nsmap).text = self.geometricalType.value
        element.find('physicalType', namespaces=nsmap).text = self.bctype.value

        element.find('pressure', namespaces=nsmap).text = self.pressure
        element.find('coupledBoundary', namespaces=nsmap).text = self.coupledBoundary
        element.replace(element.find('patchInteraction', namespaces=nsmap), self.patchInteraction.toElement())

        return element

        # return E('boundaryCondition',
        #             E('name', self.name),
        #             E('geometricalType', self.geometricalType),
        #             E('physicalType', self.bctype),
        #             E('group', '0'),
        #             E('members'),
        #             self.velocityInlet.toElement(),
        #             self.flowRateInlet.toElement(),
        #             self.flowRateOutlet.toElement(),
        #             self.pressureInlet.toElement(),
        #             self.pressureOutlet.toElement(),
        #             self.openChannelInlet.toElement(),
        #             self.openChannelOutlet.toElement(),
        #             self.freeStream.toElement(),
        #             self.farFieldRiemann.toElement(),
        #             self.subsonicInlet.toElement(),
        #             self.subsonicOutflow.toElement(),
        #             self.supersonicInflow.toElement(),
        #             self.wall.toElement(),
        #             self.thermoCoupledWall.toElement(),
        #             self.interface.toElement(),
        #             self.porousJump.toElement(),
        #             self.turbulence.toElement(),
        #             self.temperature.toElement(),
        #             self.coupledBoundary.toElement(),
        #             self.volumeFractions.toElement(),
        #             self.userDefinedScalars.toElement(),
        #             self.species.toElement(),
        #             E('pressure', self.pressure),
        #             E('fanCurveName', self.fanCurveName),
        #             self.patchInteraction.toElement(),
        #             bcid=self.bcid,
        #          )

    @staticmethod
    def fromElement(e):
        return BoundaryData(
            bcid=e.get('bcid'),
            name=e.find('name', namespaces=nsmap).text,
            geometricalType=GeometricalType(e.find('geometricalType', namespaces=nsmap).text),
            bctype=BoundaryType(e.find('physicalType', namespaces=nsmap).text),
            # velocityInlet=VelocityInlet.fromElement(e.find('velocityInlet', namespaces=nsmap)),
            wall=Wall.fromElement(e.find('wall', namespaces=nsmap)),
            # temperature=BoundaryTemperature.fromElement(e.find('temperature', namespaces=nsmap)),
            coupledBoundary=e.find('coupledBoundary', namespaces=nsmap).text,
            userDefinedScalars=userDefinedScalarsFromElement(e.find('userDefinedScalars', namespaces=nsmap)),
            # species=speciesFromElement(e.find('species', namespaces=nsmap)),
            fanCurveName=UUID(e.find('fanCurveName', namespaces=nsmap).text),
            patchInteraction=PatchInteraction.fromElement(e.find('patchInteraction', namespaces=nsmap)))
