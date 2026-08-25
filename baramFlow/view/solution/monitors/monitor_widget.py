#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.services.monitor.monitor_service import MonitorService
from .force_dialog import ForceDialog
from .point_dialog import PointDialog
from .surface_dialog import SurfaceDialog
from .volume_dialog import VolumeDialog
from .monitor_widget_ui import Ui_MonitorWidget


class MonitorWidget(QWidget):
    def __init__(self, data):
        super().__init__()
        self._ui = Ui_MonitorWidget()
        self._ui.setupUi(self)

        self._uuid = None
        self._name = None
        self._dialog = None

        self.load(data)

    @property
    def name(self):
        return self._name

    @property
    def uuid(self):
        return self._uuid

    def load(self, data=None):
        raise NotImplementedError


class ForceMonitorWidget(MonitorWidget):
    def __init__(self, data):
        super().__init__(data)

    def load(self, data=None):
        if data is None:
            data = MonitorService.getForceMonitor(self._uuid)
        else:
            self._uuid = data.monitorBase.uuid
            self._name = data.monitorBase.name
            
        region = f' ({data.region})' if data.region else ''
        self._ui.name.setText(f'{data.monitorBase.name}{region}')
        self._ui.type.setText(
            f'Force on {len(data.boundaries)} Boundaries including {BoundaryDB.getBoundaryName(data.boundaries[0])}')

    def edit(self):
        self._dialog = ForceDialog(self, self._uuid)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        MonitorService.removeForceMonitor(self._uuid)


class PointMonitorWidget(MonitorWidget):
    def __init__(self, uuid):
        super().__init__(uuid)

    def load(self, data=None):
        if data is None:
            data = MonitorService.getPointMonitor(self._uuid)
        else:
            self._uuid = data.monitorBase.uuid
            self._name = data.monitorBase.name

        self._ui.name.setText(f'{data.monitorBase.name}')
        self._ui.type.setText(f'{data.field.displayText()} on Point ({data.coordinate.x}, {data.coordinate.y}, {data.coordinate.z})')

    def edit(self):
        self._dialog = PointDialog(self, self._uuid)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        MonitorService.removePointMonitor(self.uuid)


class SurfaceMonitorWidget(MonitorWidget):
    def __init__(self, uuid):
        super().__init__(uuid)

    def load(self, data=None):
        if data is None:
            data = MonitorService.getSurfaceMonitor(self._uuid)
        else:
            self._uuid = data.monitorBase.uuid
            self._name = data.monitorBase.name

        title = MonitorDB.surfaceReportTypeToText(data.reportType)
        if data.reportType not in (SurfaceReportType.MASS_FLOW_RATE, SurfaceReportType.VOLUME_FLOW_RATE):
            title += ' ' + data.field.displayText()

        surface = BoundaryDB.getBoundaryName(data.surface)
        region = BoundaryDB.getBoundaryRegion(data.surface)

        region = f' ({region})' if region else ''
        self._ui.name.setText(f'{data.monitorBase.name}{region}')
        self._ui.type.setText(f'{title} on Surface {surface}')

    def edit(self):
        self._dialog = SurfaceDialog(self, self._uuid)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        MonitorService.removeSurfaceMonitor(self.uuid)


class VolumeMonitorWidget(MonitorWidget):
    def __init__(self, uuid):
        super().__init__(uuid)

    def load(self, data=None):
        if data is None:
            data = MonitorService.getVolumeMonitor(self._uuid)
        else:
            self._uuid = data.monitorBase.uuid
            self._name = data.monitorBase.name

        reportType = MonitorDB.volumeReportTypeToText(data.reportType)
        field = data.field.displayText()
        volume = CellZoneDB.getCellZoneName(data.volume)
        region = CellZoneDB.getCellZoneRegion(data.volume)

        region = f' ({region})' if region else ''
        self._ui.name.setText(f'{data.monitorBase.name}{region}')
        self._ui.type.setText(f'{reportType} {field} on Volume {volume}')

    def edit(self):
        self._dialog = VolumeDialog(self, self._uuid)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        MonitorService.removeVolumeMonitor(self.uuid)
