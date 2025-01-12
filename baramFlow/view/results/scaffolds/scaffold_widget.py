#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.coredb.scaffolds_db import Scaffold, ScaffoldsDB
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.view.results.scaffolds.ios_surface_dialog import IsoSurfaceDialog

from .scaffold_widget_ui import Ui_ScaffoldWidget


class ScaffoldWidget(QWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__()

        self._ui = Ui_ScaffoldWidget()
        self._ui.setupUi(self)

        self._scaffold = scaffold

        self._dialog = None

        self.load()

    @property
    def name(self):
        return self._scaffold.name

    @property
    def scaffold(self):
        return self._scaffold

    def load(self):
        raise NotImplementedError


class IsoSurfaceWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

        self._ui.type.setText('iso surface')

    def load(self):
        self._ui.name.setText(self._scaffold.name)

    def edit(self):
        self._dialog = IsoSurfaceDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()

    def _editAccepted(self):
        ScaffoldsDB().updateScaffold(self._scaffold)
        self.load()
