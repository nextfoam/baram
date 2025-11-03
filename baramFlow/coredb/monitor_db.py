#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QCoreApplication, QObject, Signal

from baramFlow.base.constants import FieldCategory
from baramFlow.base.material.material import MaterialType
from baramFlow.coredb.material_db import MaterialDB, IMaterialObserver
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType


class DirectionSpecificationMethod(Enum):
    DIRECT = 'direct'
    AOA_AOS = 'AoA_AoS'


class MonitorDBSignals(QObject):
    monitorChanged = Signal()


class MonitorDB:
    FORCE_MONITORS_XPATH   = '/monitors/forces'
    POINT_MONITORS_XPATH   = '/monitors/points'
    SURFACE_MONITORS_XPATH = '/monitors/surfaces'
    VOLUME_MONITORS_XPATH  = '/monitors/volumes'

    signals = MonitorDBSignals()

    @classmethod
    def getForceMonitorXPath(cls, name):
        return f'{cls.FORCE_MONITORS_XPATH}/forceMonitor[name="{name}"]'

    @classmethod
    def getPointMonitorXPath(cls, name):
        return f'{cls.POINT_MONITORS_XPATH}/pointMonitor[name="{name}"]'

    @classmethod
    def getSurfaceMonitorXPath(cls, name):
        return f'{cls.SURFACE_MONITORS_XPATH}/surfaceMonitor[name="{name}"]'

    @classmethod
    def getVolumeMonitorXPath(cls, name):
        return f'{cls.VOLUME_MONITORS_XPATH}/volumeMonitor[name="{name}"]'

    @classmethod
    def surfaceReportTypeToText(cls, reportType):
        return {
            SurfaceReportType.AREA_WEIGHTED_AVERAGE: QCoreApplication.translate('MonitorDB', 'Area-Weighted Average'),
            SurfaceReportType.MASS_WEIGHTED_AVERAGE: QCoreApplication.translate('MonitorDB', 'Mass-Weighted Average'),
            SurfaceReportType.INTEGRAL: QCoreApplication.translate('MonitorDB', 'Integral'),
            SurfaceReportType.MASS_FLOW_RATE: QCoreApplication.translate('MonitorDB', 'Mass Flow Rate'),
            SurfaceReportType.VOLUME_FLOW_RATE: QCoreApplication.translate('MonitorDB', 'Volume Flow Rate'),
            SurfaceReportType.MINIMUM: QCoreApplication.translate('MonitorDB', 'Minimum'),
            SurfaceReportType.MAXIMUM: QCoreApplication.translate('MonitorDB', 'Maximum'),
            SurfaceReportType.COEFFICIENT_OF_VARIATION:
                QCoreApplication.translate('MonitorDB', 'Coefficient of Variation, CoV'),
        }.get(reportType)

    @classmethod
    def volumeReportTypeToText(cls, reportType):
        return {
            VolumeReportType.VOLUME_AVERAGE: QCoreApplication.translate('MonitorDB', 'Volume Average'),
            VolumeReportType.VOLUME_INTEGRAL: QCoreApplication.translate('MonitorDB', 'Volume Integral'),
            VolumeReportType.MINIMUM: QCoreApplication.translate('MonitorDB', 'Minimum'),
            VolumeReportType.MAXIMUM: QCoreApplication.translate('MonitorDB', 'Maximum'),
            VolumeReportType.COEFFICIENT_OF_VARIATION:
                QCoreApplication.translate('MonitorDB', 'Coefficient of Variation, CoV'),
        }.get(reportType)


class MaterialObserver(IMaterialObserver):
    def materialRemoving(self, db, mid: str):
        removed = self._removeMonitors(db, mid)
        if MaterialDB.getType(mid) == MaterialType.MIXTURE:
            for sid in MaterialDB.getSpecies(mid):
                removed = self._removeMonitors(db, sid) or removed

        if removed:
            MonitorDB.signals.monitorChanged.emit()

    def specieRemoving(self, db, mid: str, primarySpecie: str):
        if self._removeMonitors(db, mid):
            MonitorDB.signals.monitorChanged.emit()

    def _removeMonitors(self, db, mid: str):
        if ModelsDB.isMultiphaseModelOn():
            category = FieldCategory.PHASE
        elif ModelsDB.isSpeciesModelOn():
            category = FieldCategory.SPECIE
        else:
            return False

        referencingFields = db.getElements(f'monitors/*/*[fieldCategory="{category.value}"][fieldCodeName="{mid}"]')
        if not referencingFields:
            return False

        for monitor in referencingFields:
            monitor.getparent().remove(monitor)

        return True
