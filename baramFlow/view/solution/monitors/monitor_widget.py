#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from .force_dialog import ForceDialog
from .point_dialog import PointDialog
from .surface_dialog import SurfaceDialog
from .volume_dialog import VolumeDialog
from .monitor_widget_ui import Ui_MonitorWidget


class MonitorWidget(QWidget):
    def __init__(self, name):
        super().__init__()
        self._ui = Ui_MonitorWidget()
        self._ui.setupUi(self)

        self._name = name
        self._dialog = None

        self.load()

    @property
    def name(self):
        return self._name

    def load(self):
        raise NotImplementedError


class ForceMonitorWidget(MonitorWidget):
    def __init__(self, name):
        super().__init__(name)

    def load(self):
        db = coredb.CoreDB()
        xpath = MonitorDB.getForceMonitorXPath(self._name)

        region = db.getValue(xpath + '/region')
        boundaries = db.getValue(xpath + '/boundaries').split()

        region = f' ({region})' if region else ''
        self._ui.name.setText(f'{self._name}{region}')
        self._ui.type.setText(
            f'Force on {len(boundaries)} Boundaries including {BoundaryDB.getBoundaryName(boundaries[0])}')

    def edit(self):
        self._dialog = ForceDialog(self, self._name)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        coredb.CoreDB().removeForceMonitor(self._name)


class PointMonitorWidget(MonitorWidget):
    def __init__(self, name):
        super().__init__(name)

    def load(self):
        db = coredb.CoreDB()
        xpath = MonitorDB.getPointMonitorXPath(self._name)

        field = FieldHelper.DBFieldKeyToText(Field(db.getValue(xpath + '/field/field')),
                                             db.getValue(xpath + '/field/fieldID'))
        coordinateX = db.getValue(xpath + '/coordinate/x')
        coordinateY = db.getValue(xpath + '/coordinate/y')
        coordinateZ = db.getValue(xpath + '/coordinate/z')
        snapOntoBoundary = db.getValue(xpath + '/snapOntoBoundary')

        self._ui.name.setText(f'{self._name}')
        self._ui.type.setText(f'{field} on Point ({coordinateX}, {coordinateY}, {coordinateZ})')

    def edit(self):
        self._dialog = PointDialog(self, self._name)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        coredb.CoreDB().removePointMonitor(self._name)


class SurfaceMonitorWidget(MonitorWidget):
    def __init__(self, name):
        super().__init__(name)

    def load(self):
        db = coredb.CoreDB()
        xpath = MonitorDB.getSurfaceMonitorXPath(self._name)

        reportType = MonitorDB.surfaceReportTypeToText(SurfaceReportType(db.getValue(xpath + '/reportType')))
        field = FieldHelper.DBFieldKeyToText(Field(db.getValue(xpath + '/field/field')),
                                             db.getValue(xpath + '/field/fieldID'))
        bcid = db.getValue(xpath + '/surface')
        surface = BoundaryDB.getBoundaryName(bcid)
        region = BoundaryDB.getBoundaryRegion(bcid)

        region = f' ({region})' if region else ''
        self._ui.name.setText(f'{self._name}{region}')
        self._ui.type.setText(f'{reportType} {field} on Surface {surface}')

    def edit(self):
        self._dialog = SurfaceDialog(self, self._name)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        coredb.CoreDB().removeSurfaceMonitor(self._name)


class VolumeMonitorWidget(MonitorWidget):
    def __init__(self, name):
        super().__init__(name)

    def load(self):
        db = coredb.CoreDB()
        xpath = MonitorDB.getVolumeMonitorXPath(self._name)

        reportType = MonitorDB.volumeReportTypeToText(VolumeReportType(db.getValue(xpath + '/reportType')))
        field = FieldHelper.DBFieldKeyToText(Field(db.getValue(xpath + '/field/field')),
                                             db.getValue(xpath + '/field/fieldID'))
        czid = db.getValue(xpath + '/volume')
        volume = CellZoneDB.getCellZoneName(czid)
        region = CellZoneDB.getCellZoneRegion(czid)

        region = f' ({region})' if region else ''
        self._ui.name.setText(f'{self._name}{region}')
        self._ui.type.setText(f'{reportType} {field} on Volume {volume}')

    def edit(self):
        self._dialog = VolumeDialog(self, self._name)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        coredb.CoreDB().removeVolumeMonitor(self._name)
