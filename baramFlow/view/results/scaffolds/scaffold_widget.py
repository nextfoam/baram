#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.scaffolds_db import Scaffold, ScaffoldsDB
from baramFlow.coredb.post_field import FIELD_TEXTS
from baramFlow.view.results.scaffolds.boundary_scaffold_dialog import BoundaryScaffoldDialog
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

    def _editAccepted(self):
        ScaffoldsDB().updateScaffold(self._scaffold)
        self.load()

    def delete(self):
        ScaffoldsDB().removeScaffold(self._scaffold)

    def load(self):
        raise NotImplementedError


class BoundaryScaffoldWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        self._ui.name.setText(self._scaffold.name)

        bcname = BoundaryDB.getBoundaryText(self._scaffold.bcid)
        self._ui.type.setText(f'boundary scaffold for <b>{bcname}</b>')

    def edit(self):
        self._dialog = BoundaryScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()


class IsoSurfaceWidget(ScaffoldWidget):
    def __init__(self, scaffold: Scaffold):
        super().__init__(scaffold)

    def load(self):
        self._ui.name.setText(self._scaffold.name)

        if self._scaffold.field in FIELD_TEXTS:
            fieldName = FIELD_TEXTS[self._scaffold.field]
        else:
            fieldName = self._scaffold.field.name

        self._ui.type.setText(f'iso surface for field <b>{fieldName}</b>')

    def edit(self):
        self._dialog = IsoSurfaceDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()

