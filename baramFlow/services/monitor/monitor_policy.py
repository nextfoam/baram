#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from baramFlow.base.constants import FieldCategory
from baramFlow.base.field import ALL_PHASES, ALL_SPECIES
from baramFlow.base.material.constants import MaterialType
from baramFlow.base.monitor.monitor import SurfaceMonitorConfiguration
from baramFlow.base.region.region_patch import RegionMaterialsUpdate
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.services.material.material_service import MaterialService
from baramFlow.services.monitor.monitor_service import MonitorService
from baramFlow.services.region.region_service import RegionService


class MonitorPolicy:
    @staticmethod
    def validateSurfaceMonitor(monitor: SurfaceMonitorConfiguration):
        region = RegionService.getRegion(BoundaryService.getBoundary(monitor.surface).rname)

        MonitorPolicy._checkSurfaceMaterial(monitor, region.material, region.secondaryMaterials)

    @staticmethod
    def checkRegionMaterialUpdateRequest(data: RegionMaterialsUpdate):
        for monitor in MonitorService.getSurfaceMonitors():
            rname = BoundaryService.getBoundary(monitor.surface).rname
            if rname == data.rname:
                try:
                    MonitorPolicy._checkSurfaceMaterial(monitor, data.material, data.secondaryMaterials)
                except ValueError as e:
                    raise ValueError(
                        QCoreApplication.translate(
                            'MonitorPolicy',
                            'Material composition changes are restricted by the surface monitor "{0}\n- {1}"').format(
                            monitor.monitorBase.name, str(e)))

    @staticmethod
    def _checkSurfaceMaterial(monitor: SurfaceMonitorConfiguration, material, secondaryMaterials):
        if ModelsDB.isMultiphaseModelOn():
            if monitor.field.field.category != FieldCategory.PHASE or monitor.field.field == ALL_PHASES:
                return

            mid = monitor.field.field.codeName
            if mid not in secondaryMaterials:
                raise ValueError(
                    QCoreApplication.translate(
                        'MonitorPolicy',
                        '{0} is not a substance present in the region to which the surface belongs.'.format(
                            MaterialService.getName(mid))))
        elif ModelsDB.isSpeciesModelOn():
            if monitor.field.field.category != FieldCategory.SPECIE or monitor.field.field == ALL_SPECIES:
                return

            if MaterialService.getMaterial(material).type == MaterialType.MIXTURE:
                sid = monitor.field.field.codeName
                if sid not in MaterialService.getSpeciesInMixture(material):
                    raise ValueError(
                        QCoreApplication.translate(
                            'MonitorPolicy',
                            '{0} is not a substance present in the region to which the surface belongs.'.format(
                                MaterialService.getName(sid))))
            elif material != monitor.field.field.codeName:
                raise ValueError(
                    QCoreApplication.translate(
                        'MonitorPolicy',
                        '{0} is not a substance present in the region to which the surface belongs.'.format(
                            MaterialService.getName(monitor.field.field.codeName))))

