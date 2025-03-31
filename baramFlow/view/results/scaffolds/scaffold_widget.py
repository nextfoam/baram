#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtGui import QFontMetrics, Qt
from PySide6.QtWidgets import QWidget

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.boundary_scaffold import BoundaryScaffold
from baramFlow.coredb.disk_scaffold import DiskScaffold
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.scaffolds_db import Scaffold, ScaffoldsDB
from baramFlow.coredb.post_field import FIELD_TEXTS
from baramFlow.view.results.scaffolds.boundary_scaffold_dialog import BoundaryScaffoldDialog
from baramFlow.view.results.scaffolds.disk_scaffold_dialog import DiskScaffoldDialog
from baramFlow.view.results.scaffolds.iso_surface_dialog import IsoSurfaceDialog

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
        await self._scaffold.markUpdated()
        self.load()

    async def delete(self):
        await ScaffoldsDB().removeScaffold(self._scaffold)

    def load(self):
        raise NotImplementedError


class BoundaryScaffoldWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: BoundaryScaffold = self._scaffold

        self._ui.name.setText(scaffold.name)

        bcNamesList = [BoundaryDB.getBoundaryText(bcid) for bcid in scaffold.boundaries]
        bcNames = ', '.join(bcNamesList)
        metrics = QFontMetrics(self._ui.type.font())
        elidedText = metrics.elidedText(bcNames, Qt.TextElideMode.ElideRight, 100);

        self._ui.type.setText(f'boundary scaffold for <b>{elidedText}</b>')

    def edit(self):
        self._dialog = BoundaryScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class IsoSurfaceWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        scaffold: IsoSurface = self._scaffold
        self._ui.name.setText(scaffold.name)

        if scaffold.field in FIELD_TEXTS:
            fieldName = FIELD_TEXTS[scaffold.field]
        else:
            fieldName = scaffold.field.codeName

        self._ui.type.setText(f'iso surface for field <b>{fieldName}</b>')

    def edit(self):
        self._dialog = IsoSurfaceDialog(self, self._scaffold)
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

