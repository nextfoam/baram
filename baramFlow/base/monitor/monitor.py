#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from enum import Enum, auto
from uuid import uuid4, UUID

from libbaram.natural_name_uuid import uuidToNnstr
from libbaram.pfloat import PFloat

from baramFlow.base.base import DirectionSpecificationMethod, Vector
from baramFlow.base.constants import FieldType, VectorComponent
from baramFlow.base.field import getFieldInstance, Field, PRESSURE
from baramFlow.coredb.coredb import CoreDB, nsmap
from baramFlow.coredb.libdb import xmlToBool, xmlToStr, E, ValueException, dbErrorToMessage
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.openfoam.solver_field import getSolverComponentName, getSolverFieldName

FORCE_MONITORS_XPATH   = '/monitors/forces'
POINT_MONITORS_XPATH   = '/monitors/points'
SURFACE_MONITORS_XPATH = '/monitors/surfaces'
VOLUME_MONITORS_XPATH  = '/monitors/volumes'

FORCE_MONITOR_XPATH   = '/monitors/forces/forceMonitor'
POINT_MONITOR_XPATH   = '/monitors/points/pointMonitor'
SURFACE_MONITOR_XPATH = '/monitors/surfaces/surfaceMonitor'
VOLUME_MONITOR_XPATH  = '/monitors/volumes/volumeMonitor'


class MonitorType(Enum):
    FORCE = auto()
    POINT = auto()
    SURFACE = auto()
    VOLUME = auto()


BASE_NAMES = {
    MonitorType.FORCE:      'force-mon',
    MonitorType.POINT:      'point-mon',
    MonitorType.SURFACE:    'surface-mon',
    MonitorType.VOLUME:     'volume-mon'
}


def _forceMonitorXPath(uuid):
    return f'{FORCE_MONITOR_XPATH}[uuid="{uuid}"]'


def _pointMonitorXPath(uuid):
    return f'{POINT_MONITOR_XPATH}[uuid="{uuid}"]'


def _surfaceMonitorXPath(uuid):
    return f'{SURFACE_MONITOR_XPATH}[uuid="{uuid}"]'


def _volumeMonitorXPath(uuid):
    return f'{VOLUME_MONITOR_XPATH}[uuid="{uuid}"]'


def _forceMonitor(uuid):
    return CoreDB().getElement(f'{FORCE_MONITOR_XPATH}[uuid="{uuid}"]')


def _pointMonitor(uuid):
    return CoreDB().getElement(f'{POINT_MONITOR_XPATH}[uuid="{uuid}"]')


def _surfaceMonitor(uuid):
    return CoreDB().getElement(f'{SURFACE_MONITOR_XPATH}[uuid="{uuid}"]')


def _volumeMonitor(uuid):
    return CoreDB().getElement(f'{VOLUME_MONITOR_XPATH}[uuid="{uuid}"]')


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

    @classmethod
    def newName(cls, monitorType):
        i = 1
        name = f'{BASE_NAMES[monitorType]}-1'
        while MonitorManager.isExistingName(name):
            i += 1
            name = f'{BASE_NAMES[monitorType]}-{i}'

        return name

    @staticmethod
    def fromElement(e, monitorType):
        return MonitorBaseConfiguration(
            type=monitorType,
            uuid=UUID(e.find('uuid', namespaces=nsmap).text),
            name=e.find('name', namespaces=nsmap).text,
            writeInterval=e.find('writeInterval', namespaces=nsmap).text,
            functionName=e.find('functionName', namespaces=nsmap).text)

    @classmethod
    def new(cls, monitorType):
        uuid = uuid4()

        return MonitorBaseConfiguration(
            type=monitorType,
            uuid=uuid,
            name=cls.newName(monitorType),
            writeInterval='1',
            functionName=uuidToNnstr(uuid))


@dataclass
class ForceDirection:
    specificationMethod: DirectionSpecificationMethod   = DirectionSpecificationMethod.DIRECT
    dragDirection: Vector                               = field(default_factory= Vector.xUnit)
    liftDirection: Vector                               = field(default_factory= Vector.yUnit)
    angleOfAttack: PFloat                               = field(default_factory=lambda: PFloat('0'))
    angleOfSideslip: PFloat                             = field(default_factory=lambda: PFloat('0'))

    @staticmethod
    def fromElement(e):
        return ForceDirection(
            specificationMethod=DirectionSpecificationMethod(e.find('specificationMethod', namespaces=nsmap).text),
            dragDirection=Vector.fromElement(e.find('dragDirection', namespaces=nsmap)),
            liftDirection=Vector.fromElement(e.find('liftDirection', namespaces=nsmap)),
            angleOfAttack=PFloat(e.find('angleOfAttack', namespaces=nsmap).text),
            angleOfSideslip=PFloat(e.find('angleOfSideslip', namespaces=nsmap).text))

    def toElement(self):
        return E('forceDirection',  E.specificationMethod(self.specificationMethod.value),
                                    self.dragDirection.toElement('dragDirection'),
                                    self.liftDirection.toElement('liftDirection'),
                                    E.angleOfAttack(str(self.angleOfAttack)),
                                    E.angleOfSideslip(str(self.angleOfSideslip)))


@dataclass
class ForceMonitorConfiguration:
    monitorBase: MonitorBaseConfiguration
    forceDirection: ForceDirection
    centerOfRotation: Vector
    region: str
    boundaries: list[str]
    pitchAxisDirection: Vector = field(default_factory=Vector.yUnit)

    @classmethod
    def new(cls):
        return ForceMonitorConfiguration(
            monitorBase=MonitorBaseConfiguration.new(MonitorType.FORCE),
            forceDirection=ForceDirection(),
            centerOfRotation=Vector.zero(),
            region='',
            boundaries=[])

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
    field: MonitorField
    coordinate: Vector
    snapOntoBoundary: str = '0'
    region: str = ''
    interval: str = '1'

    @classmethod
    def new(cls):
        return PointMonitorConfiguration(
            monitorBase=MonitorBaseConfiguration.new(MonitorType.POINT),
            field=MonitorField(PRESSURE, VectorComponent.MAGNITUDE),
            coordinate=Vector.zero())

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
    reportType: SurfaceReportType
    field: MonitorField
    surface: str

    @classmethod
    def new(cls):
        return SurfaceMonitorConfiguration(
            monitorBase=MonitorBaseConfiguration.new(MonitorType.SURFACE),
            reportType=SurfaceReportType.AREA_WEIGHTED_AVERAGE,
            field=MonitorField(PRESSURE, VectorComponent.MAGNITUDE),
            surface='0')

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
    reportType: VolumeReportType
    field: MonitorField
    volume: str

    @classmethod
    def new(cls):
        return VolumeMonitorConfiguration(
            monitorBase=MonitorBaseConfiguration.new(MonitorType.VOLUME),
            reportType=VolumeReportType.VOLUME_AVERAGE,
            field=MonitorField(PRESSURE, VectorComponent.MAGNITUDE),
            volume='0')

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


class MonitorManager:
    @staticmethod
    def isExistingName(name):
        return CoreDB().exists(f'monitors/*/*[name="{name}"]')

    @staticmethod
    def getForceMonitors():
        return [ForceMonitorConfiguration.fromElement(e) for e in CoreDB().getElements(FORCE_MONITOR_XPATH)]

    @staticmethod
    def getPointMonitors():
        return [PointMonitorConfiguration.fromElement(e) for e in CoreDB().getElements(POINT_MONITOR_XPATH)]

    @staticmethod
    def getSurfaceMonitors():
        return [SurfaceMonitorConfiguration.fromElement(e) for e in CoreDB().getElements(SURFACE_MONITOR_XPATH)]

    @staticmethod
    def getVolumeMonitors():
        return [VolumeMonitorConfiguration.fromElement(e) for e in CoreDB().getElements(VOLUME_MONITOR_XPATH)]

    @staticmethod
    def getForceMonitor(uuid):
        return ForceMonitorConfiguration.fromElement(_forceMonitor(uuid))

    @staticmethod
    def getPointMonitor(uuid):
        return PointMonitorConfiguration.fromElement(_pointMonitor(uuid))

    @staticmethod
    def getSurfaceMonitor(uuid):
        return SurfaceMonitorConfiguration.fromElement(_surfaceMonitor(uuid))

    @staticmethod
    def getVolumeMonitor(uuid):
        return VolumeMonitorConfiguration.fromElement(_volumeMonitor(uuid))

    @staticmethod
    def newForceMonitor():
        return ForceMonitorConfiguration.new()

    @staticmethod
    def newPointMonitor():
        return PointMonitorConfiguration.new()

    @staticmethod
    def newSurfaceMonitor():
        return SurfaceMonitorConfiguration.new()

    @staticmethod
    def newVolumeMonitor():
        return VolumeMonitorConfiguration.new()

    @staticmethod
    def addForceMonitor(data: ForceMonitorConfiguration):
        CoreDB().addElement(FORCE_MONITORS_XPATH, data.toElement())

    @staticmethod
    def addPointMonitor(data: PointMonitorConfiguration):
        CoreDB().addElement(POINT_MONITORS_XPATH, data.toElement())

    @staticmethod
    def addSurfaceMonitor(data:SurfaceMonitorConfiguration):
        CoreDB().addElement(SURFACE_MONITORS_XPATH, data.toElement())

    @staticmethod
    def addVolumeMonitor(data: VolumeMonitorConfiguration):
        CoreDB().addElement(VOLUME_MONITORS_XPATH, data.toElement())

    @staticmethod
    def updateForceMonitor(data: ForceMonitorConfiguration):
        xpath = _forceMonitorXPath(data.monitorBase.uuid)
        try:
            with CoreDB() as db:
                db.setValue(xpath + '/writeInterval', data.monitorBase.writeInterval)

                db.setValue(xpath + '/forceDirection/specificationMethod', data.forceDirection.specificationMethod.value)
                db.replaceElement(xpath + '/forceDirection/dragDirection',
                                  data.forceDirection.dragDirection.toElement('dragDirection'))
                db.replaceElement(xpath + '/forceDirection/liftDirection',
                                  data.forceDirection.liftDirection.toElement('liftDirection'))

                if data.forceDirection.specificationMethod == DirectionSpecificationMethod.AOA_AOS:
                    db.setValue(xpath + '/forceDirection/angleOfSideslip', data.forceDirection.angleOfSideslip)
                    db.setValue(xpath + '/forceDirection/angleOfAttack', data.forceDirection.angleOfAttack)

                db.replaceElement(xpath + '/centerOfRotation', data.centerOfRotation.toElement('centerOfRotation'))
                db.setValue(xpath + '/region', data.region)
                db.setValue(xpath + '/boundaries', ' ' .join(data.boundaries))
        except ValueException as e:
            raise ValueError(dbErrorToMessage(e))

    @staticmethod
    def updatePointMonitor(data: PointMonitorConfiguration):
        xpath = _pointMonitorXPath(data.monitorBase.uuid)
        try:
            with CoreDB() as db:
                db.setValue(xpath + '/writeInterval', data.monitorBase.writeInterval)

                db.setValue(xpath + '/fieldCategory', data.field.field.category.value)
                db.setValue(xpath + '/fieldCodeName', data.field.field.codeName)
                db.setValue(xpath + '/fieldComponent', str(data.field.component.value))
                db.replaceElement(xpath + '/coordinate', data.coordinate.toElement('coordinate'))
                db.setValue(xpath + '/snapOntoBoundary', 'false' if data.snapOntoBoundary == '0' else 'true')
                db.setValue(xpath + '/boundary', data.snapOntoBoundary)
                db.setValue(xpath + '/region', data.region)
        except ValueException as e:
            raise ValueError(dbErrorToMessage(e))

    @staticmethod
    def updateSurfaceMonitor(data: SurfaceMonitorConfiguration):
        xpath = _surfaceMonitorXPath(data.monitorBase.uuid)
        try:
            with CoreDB() as db:
                db.setValue(xpath + '/writeInterval', data.monitorBase.writeInterval)

                db.setValue(xpath + '/reportType', data.reportType.value)
                db.setValue(xpath + '/fieldCategory', data.field.field.category.value)
                db.setValue(xpath + '/fieldCodeName', data.field.field.codeName)
                db.setValue(xpath + '/fieldComponent', str(data.field.component.value))
                db.setValue(xpath + '/surface', data.surface)
        except ValueException as e:
            raise ValueError(dbErrorToMessage(e))

    @staticmethod
    def updateVolumeMonitor(data: VolumeMonitorConfiguration):
        xpath = _volumeMonitorXPath(data.monitorBase.uuid)
        try:
            with CoreDB() as db:
                db.setValue(xpath + '/writeInterval', data.monitorBase.writeInterval)

                db.setValue(xpath + '/reportType', data.reportType.value)
                db.setValue(xpath + '/fieldCategory', data.field.field.category.value)
                db.setValue(xpath + '/fieldCodeName', data.field.field.codeName)
                db.setValue(xpath + '/fieldComponent', str(data.field.component.value))
                db.setValue(xpath + '/volume', data.volume)
        except ValueException as e:
            raise ValueError(dbErrorToMessage(e))

    @staticmethod
    def updatePointMonitorRegion(uuid, region):
        CoreDB().setValue(_pointMonitorXPath(uuid) + '/region', region)

    @staticmethod
    def removeForceMonitor(uuid):
        CoreDB().removeElement(_forceMonitorXPath(uuid))

    @staticmethod
    def removePointMonitor(uuid):
        CoreDB().removeElement(_pointMonitorXPath(uuid))

    @staticmethod
    def removeSurfaceMonitor(uuid):
        CoreDB().removeElement(_surfaceMonitorXPath(uuid))

    @staticmethod
    def removeVolumeMonitor(uuid):
        CoreDB().removeElement(_volumeMonitorXPath(uuid))

    @staticmethod
    def clearMonitors():
        db = CoreDB()
        db.clearElement(FORCE_MONITORS_XPATH)
        db.clearElement(POINT_MONITORS_XPATH)
        db.clearElement(SURFACE_MONITORS_XPATH)
        db.clearElement(VOLUME_MONITORS_XPATH)
