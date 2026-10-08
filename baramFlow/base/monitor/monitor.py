#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum, auto
from uuid import UUID

from libbaram.pfloat import PFloat

from baramFlow.base.base import DirectionSpecificationMethod, Vector
from baramFlow.base.constants import FieldType, VectorComponent
from baramFlow.base.field import getFieldInstance, Field, PRESSURE
from baramFlow.coredb.coredb import nsmap
from baramFlow.coredb.libdb import xmlToBool, xmlToStr, E
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.openfoam.solver_field import getSolverComponentName, getSolverFieldName


class MonitorType(Enum):
    FORCE = auto()
    POINT = auto()
    SURFACE = auto()
    VOLUME = auto()


@dataclass
class MonitorField:
    field: Field
    component: VectorComponent

    def displayText(self):
        if self.field.type == FieldType.SCALAR:
            return self.field.text

        if self.component == VectorComponent.X:
            component = 'X'
        elif self.component == VectorComponent.Y:
            component = 'Y'
        elif self.component == VectorComponent.Z:
            component = 'Z'
        else:
            component = 'Magnitude'

        return f'{component}-{self.field.text}'

    def openfoamField(self):
        if self.field.type == FieldType.VECTOR:
            return getSolverComponentName(self.field, self.component)

        return getSolverFieldName(self.field)


def getMonitorField(element):
    return MonitorField(getFieldInstance(element.find('fieldCategory', namespaces=nsmap).text,
                                         element.find('fieldCodeName', namespaces=nsmap).text),
                        VectorComponent(int(element.find('fieldComponent', namespaces=nsmap).text)))


@dataclass
class MonitorBaseConfiguration:
    type: MonitorType
    uuid: UUID
    name: str
    writeInterval: str
    functionName: str = None
    showChart: bool = True

    @staticmethod
    def fromElement(e, monitorType):
        return MonitorBaseConfiguration(
            type=monitorType,
            uuid=UUID(e.find('uuid', namespaces=nsmap).text),
            name=e.find('name', namespaces=nsmap).text,
            writeInterval=e.find('writeInterval', namespaces=nsmap).text,
            functionName=e.find('functionName', namespaces=nsmap).text)


@dataclass
class ForceDirection:
    specificationMethod: DirectionSpecificationMethod   = DirectionSpecificationMethod.DIRECT
    dragDirection: Vector                               = dataClassField(default_factory= Vector.xUnit)
    liftDirection: Vector                               = dataClassField(default_factory= Vector.yUnit)
    angleOfAttack: PFloat                               = dataClassField(default_factory=lambda: PFloat('0'))
    angleOfSideslip: PFloat                             = dataClassField(default_factory=lambda: PFloat('0'))

    @staticmethod
    def fromElement(e):
        return ForceDirection(
            specificationMethod=DirectionSpecificationMethod(e.find('specificationMethod', namespaces=nsmap).text),
            dragDirection=Vector.fromElement(e.find('dragDirection', namespaces=nsmap)),
            liftDirection=Vector.fromElement(e.find('liftDirection', namespaces=nsmap)),
            angleOfAttack=PFloat.fromElement(e.find('angleOfAttack', namespaces=nsmap)),
            angleOfSideslip=PFloat.fromElement(e.find('angleOfSideslip', namespaces=nsmap)))

    def toElement(self):
        return E('forceDirection',  E.specificationMethod(self.specificationMethod.value),
                 self.dragDirection.toElement('dragDirection'),
                 self.liftDirection.toElement('liftDirection'),
                 self.angleOfAttack.toElement('angleOfAttack'),
                 self.angleOfSideslip.toElement('angleOfSideslip'))


@dataclass
class ForceMonitorConfiguration:
    monitorBase: MonitorBaseConfiguration
    forceDirection: ForceDirection  = dataClassField(default_factory=ForceDirection)
    centerOfRotation: Vector        = dataClassField(default_factory=Vector.zero)
    region: str                     = ''
    boundaries: list[str]           = dataClassField(default_factory=list)
    pitchAxisDirection: Vector      = dataClassField(default_factory=Vector.yUnit)

    @staticmethod
    def fromElement(e):
        return ForceMonitorConfiguration(
            monitorBase=MonitorBaseConfiguration.fromElement(e, MonitorType.FORCE),
            forceDirection=ForceDirection.fromElement(e.find('forceDirection', namespaces=nsmap)),
            centerOfRotation=Vector.fromElement(e.find('centerOfRotation', namespaces=nsmap)),
            region=xmlToStr(e.find('region', namespaces=nsmap).text),
            boundaries=e.find('boundaries', namespaces=nsmap).text.split())

    def toElement(self):
        return E('forceMonitor',    E('uuid',          self.monitorBase.uuid),
                                    E('name',             self.monitorBase.name),
                                    E('showChart',        self.monitorBase.showChart),
                                    E('writeInterval',    self.monitorBase.writeInterval),
                                    self.forceDirection.toElement(),
                                    self.pitchAxisDirection.toElement('pitchAxisDirection'),
                                    self.centerOfRotation.toElement('centerOfRotation'),
                                    E('region',           self.region),
                                    E('boundaries',       ' ' .join(self.boundaries)),
                                    E('functionName',     self.monitorBase.functionName))


@dataclass
class PointMonitorConfiguration:
    monitorBase: MonitorBaseConfiguration
    field: MonitorField         = dataClassField(default_factory=lambda: MonitorField(PRESSURE,
                                                                                      VectorComponent.MAGNITUDE))
    coordinate: Vector          = dataClassField(default_factory=Vector.zero)
    snapOntoBoundary: str       = '0'
    region: str                 = ''
    interval: str               = '1'

    @staticmethod
    def fromElement(e):
        snapOntoBoundary = xmlToBool(e.find('snapOntoBoundary', namespaces=nsmap).text)
        return PointMonitorConfiguration(
            monitorBase=MonitorBaseConfiguration.fromElement(e, MonitorType.POINT),
            field=getMonitorField(e),
            coordinate=Vector.fromElement(e.find('coordinate', namespaces=nsmap)),
            snapOntoBoundary=e.find('boundary', namespaces=nsmap).text if snapOntoBoundary else '0',
            region=xmlToStr(e.find('region', namespaces=nsmap).text))

    def toElement(self):
        return E('pointMonitor',    E('uuid',             self.monitorBase.uuid),
                                    E('name',             self.monitorBase.name),
                                    E('showChart',        self.monitorBase.showChart),
                                    E('writeInterval',    self.monitorBase.writeInterval),
                                    E('fieldCategory',    self.field.field.category),
                                    E('fieldCodeName',    self.field.field.codeName),
                                    E('fieldComponent',   str(self.field.component)),
                                    E('interval',         self.interval),
                                    self.coordinate.toElement('coordinate'),
                                    E('snapOntoBoundary', self.snapOntoBoundary != '0'),
                                    E('boundary',         self.snapOntoBoundary),
                                    E('region',           self.region),
                                    E('functionName',     self.monitorBase.functionName))


@dataclass
class SurfaceMonitorConfiguration:
    monitorBase: MonitorBaseConfiguration
    reportType: SurfaceReportType   = SurfaceReportType.AREA_WEIGHTED_AVERAGE
    field: MonitorField             = dataClassField(default_factory=lambda: MonitorField(PRESSURE,
                                                                                          VectorComponent.MAGNITUDE))
    surface: str                    = '0'

    @staticmethod
    def fromElement(e):
        return SurfaceMonitorConfiguration(monitorBase=MonitorBaseConfiguration.fromElement(e, MonitorType.SURFACE),
                                           reportType=SurfaceReportType(e.find('reportType', namespaces=nsmap).text),
                                           field=getMonitorField(e),
                                           surface=e.find('surface', namespaces=nsmap).text)

    def toElement(self):
        return E('surfaceMonitor',  E('uuid',           self.monitorBase.uuid),
                                    E('name',           self.monitorBase.name),
                                    E('showChart',      self.monitorBase.showChart),
                                    E('writeInterval',  self.monitorBase.writeInterval),
                                    E('reportType',     self.reportType),
                                    E('fieldCategory',  self.field.field.category),
                                    E('fieldCodeName',  self.field.field.codeName),
                                    E('fieldComponent', str(self.field.component)),
                                    E('surface',        self.surface),
                                    E('functionName',   self.monitorBase.functionName))


@dataclass
class VolumeMonitorConfiguration:
    monitorBase: MonitorBaseConfiguration
    reportType: VolumeReportType    = VolumeReportType.VOLUME_AVERAGE
    field: MonitorField             = dataClassField(default_factory=lambda: MonitorField(PRESSURE,
                                                                                          VectorComponent.MAGNITUDE))
    volume: str                     = '0'

    @staticmethod
    def fromElement(e):
        return VolumeMonitorConfiguration(monitorBase=MonitorBaseConfiguration.fromElement(e, MonitorType.VOLUME),
                                          reportType=VolumeReportType(e.find('reportType', namespaces=nsmap).text),
                                          field=getMonitorField(e),
                                          volume=e.find('volume', namespaces=nsmap).text)

    def toElement(self):
        return E('volumeMonitor',   E('uuid',            self.monitorBase.uuid),
                                    E('name',            self.monitorBase.name),
                                    E('showChart',       self.monitorBase.showChart),
                                    E('writeInterval',   self.monitorBase.writeInterval),
                                    E('reportType',      self.reportType),
                                    E('fieldCategory',   self.field.field.category),
                                    E('fieldCodeName',   self.field.field.codeName),
                                    E('fieldComponent',  str(self.field.component)),
                                    E('volume',          self.volume),
                                    E('functionName',    self.monitorBase.functionName))
