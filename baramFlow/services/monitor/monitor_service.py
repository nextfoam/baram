#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import uuid4

from baramFlow.base.base import DirectionSpecificationMethod
from baramFlow.base.monitor.monitor import MonitorBaseConfiguration, MonitorType
from baramFlow.base.monitor.monitor import ForceMonitorConfiguration, PointMonitorConfiguration
from baramFlow.base.monitor.monitor import SurfaceMonitorConfiguration, VolumeMonitorConfiguration
from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from libbaram.natural_name_uuid import uuidToNnstr

FORCE_MONITORS_XPATH   = '/monitors/forces'
POINT_MONITORS_XPATH   = '/monitors/points'
SURFACE_MONITORS_XPATH = '/monitors/surfaces'
VOLUME_MONITORS_XPATH  = '/monitors/volumes'

FORCE_MONITOR_XPATH   = '/monitors/forces/forceMonitor'
POINT_MONITOR_XPATH   = '/monitors/points/pointMonitor'
SURFACE_MONITOR_XPATH = '/monitors/surfaces/surfaceMonitor'
VOLUME_MONITOR_XPATH  = '/monitors/volumes/volumeMonitor'


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


def _newName(monitorType):
    i = 1
    name = f'{BASE_NAMES[monitorType]}-1'
    while MonitorService.isExistingName(name):
        i += 1
        name = f'{BASE_NAMES[monitorType]}-{i}'

    return name


def _newMonitorBase(monitorType: MonitorType):
    uuid = uuid4()

    return MonitorBaseConfiguration(
        type=monitorType,
        uuid=uuid,
        name=_newName(monitorType),
        writeInterval='1',
        functionName=uuidToNnstr(uuid))


class MonitorService:
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
        return ForceMonitorConfiguration(
            monitorBase=_newMonitorBase(MonitorType.FORCE))

    @staticmethod
    def newPointMonitor():
        return PointMonitorConfiguration(
            monitorBase=_newMonitorBase(MonitorType.POINT))

    @staticmethod
    def newSurfaceMonitor():
        return SurfaceMonitorConfiguration(
            monitorBase=_newMonitorBase(MonitorType.SURFACE))

    @staticmethod
    def newVolumeMonitor():
        return VolumeMonitorConfiguration(
            monitorBase=_newMonitorBase(MonitorType.VOLUME))

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
                    db.setValue(xpath + '/forceDirection/angleOfSideslip', str(data.forceDirection.angleOfSideslip))
                    db.setValue(xpath + '/forceDirection/angleOfAttack', str(data.forceDirection.angleOfAttack))

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
