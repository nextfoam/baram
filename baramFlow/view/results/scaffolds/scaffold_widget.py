#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtGui import QFontMetrics, Qt
from PySide6.QtWidgets import QWidget

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.base.scaffold.boundary_scaffold import BoundaryScaffold
from baramFlow.base.scaffold.disk_scaffold import DiskScaffold
from baramFlow.base.scaffold.iso_surface import IsoSurface
from baramFlow.base.scaffold.line_scaffold import LineScaffold
from baramFlow.base.scaffold.parallelogram import Parallelogram
from baramFlow.base.scaffold.plane_scaffold import PlaneScaffold
from baramFlow.base.scaffold.scaffolds_db import Scaffold, ScaffoldsDB
from baramFlow.base.scaffold.sphere_scaffold import SphereScaffold
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.view.results.scaffolds.boundary_scaffold_dialog import BoundaryScaffoldDialog
from baramFlow.view.results.scaffolds.disk_scaffold_dialog import DiskScaffoldDialog
from baramFlow.view.results.scaffolds.iso_surface_dialog import IsoSurfaceDialog
from baramFlow.view.results.scaffolds.line_scaffold_dialog import LineScaffoldDialog
from baramFlow.view.results.scaffolds.parallelogram_dialog import ParallelogramDialog
from baramFlow.view.results.scaffolds.plane_scaffold_dialog import PlaneScaffoldDialog
from baramFlow.view.results.scaffolds.sphere_scaffold_dialog import SphereScaffoldDialog
from widgets.progress_dialog import ProgressDialog

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

    @qasync.asyncSlot()
    async def _editAccepted(self):
        progressDialog = ProgressDialog(self, self.tr('Scaffold Parameters'), openDelay=500)
        progressDialog.setLabelText(self.tr('Applying Scaffold parameters...'))
        progressDialog.open()

        await self._scaffold.markUpdated()
        self.load()

        progressDialog.close()

    async def delete(self):
        await ScaffoldsDB().removeScaffold(self._scaffold)

    def load(self):
        raise NotImplementedError

    def edit(self):
        raise NotImplementedError


class BoundaryScaffoldWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: BoundaryScaffold = self._scaffold

        self._ui.name.setText(scaffold.name)

        #
        # Cannot find a way to update this information when boundary names are changed by importing mesh
        #
        # bcNamesList = [BoundaryDB.getBoundaryText(bcid) for bcid in scaffold.boundaries]
        # bcNames = ', '.join(bcNamesList)
        # metrics = QFontMetrics(self._ui.type.font())
        # elidedText = metrics.elidedText(bcNames, Qt.TextElideMode.ElideRight, 100)

        # self._ui.type.setText(f'boundary scaffold for <b>{elidedText}</b>')
        self._ui.type.setText(f'boundary scaffold')

    def edit(self):
        self._dialog = BoundaryScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class DiskScaffoldWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: DiskScaffold = self._scaffold
        self._ui.name.setText(scaffold.name)

        self._ui.type.setText(f'Disk of Outer Radius <b>{scaffold.outerRadius}</b> at({scaffold.centerX}, {scaffold.centerY}, {scaffold.centerZ})')

    def edit(self):
        self._dialog = DiskScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class IsoSurfaceWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: IsoSurface = self._scaffold
        self._ui.name.setText(scaffold.name)

        self._ui.type.setText(f'iso surface for field <b>{scaffold.field.text}</b>')

    def edit(self):
        self._dialog = IsoSurfaceDialog(self, self._scaffold, FileSystem.times())
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class LineScaffoldWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: LineScaffold = self._scaffold
        self._ui.name.setText(scaffold.name)

        self._ui.type.setText(f'Line between ({scaffold.point1X}, {scaffold.point1Y}, {scaffold.point1Z}) and ({scaffold.point2X}, {scaffold.point2Y}, {scaffold.point2Z})')

    def edit(self):
        self._dialog = LineScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class ParallelogramWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: Parallelogram = self._scaffold
        self._ui.name.setText(scaffold.name)

        self._ui.type.setText(f'Parallelogram at origin ({scaffold.originX}, {scaffold.originY}, {scaffold.originZ})')

    def edit(self):
        self._dialog = ParallelogramDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class PlaneScaffoldWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: PlaneScaffold = self._scaffold
        self._ui.name.setText(scaffold.name)

        self._ui.type.setText(f'Plane at ({scaffold.originX}, {scaffold.originY}, {scaffold.originZ}) with Normal of ({scaffold.normalX}, {scaffold.normalY}, {scaffold.normalZ})')

    def edit(self):
        self._dialog = PlaneScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class SphereScaffoldWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: SphereScaffold = self._scaffold
        self._ui.name.setText(scaffold.name)

        self._ui.type.setText(f'Sphere at ({scaffold.centerX}, {scaffold.centerY}, {scaffold.centerZ}) with R={str(scaffold.radius)}')

    def edit(self):
        self._dialog = SphereScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()

