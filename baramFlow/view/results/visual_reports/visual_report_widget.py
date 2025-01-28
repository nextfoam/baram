#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from .contours_dialog import ContoursDialog

from .graphics_widget_ui import Ui_GraphicsWidget


class GraphicsWidget(QWidget):
    def __init__(self, name):
        super().__init__()

        self._ui = Ui_GraphicsWidget()
        self._ui.setupUi(self)

        self._name = name
        self._dialog = None

        # self.load()

    @property
    def name(self):
        return self._name

    def load(self):
        raise NotImplementedError


class ContoursWidget(GraphicsWidget):
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
        self._dialog = ContoursDialog(self, self._name)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def delete(self):
        coredb.CoreDB().removeForceMonitor(self._name)

