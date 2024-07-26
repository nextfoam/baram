#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog, QFileDialog

from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog, SelectorItem

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType
from baramMesh.openfoam.system.extrude_mesh_dict import ExtrudeOptions, ExtrudeModel
from .export_2D_plane_dialog_ui import Ui_Export2DPlaneDialog


class Export2DPlaneDialog(QDialog):
    def __init__(self, parent, path=None):
        super().__init__(parent)

        self._ui = Ui_Export2DPlaneDialog()
        self._ui.setupUi(self)

        self._baseLocation = Path.home() if path is None else path
        self._updateProjectLocation()

        self._dialog = None

        self._connectSignalsSlots()

    def projectLocation(self):
        return Path(self._ui.projectLocation.text())

    def extrudeOptions(self):
        return ExtrudeOptions(self._ui.boundary.text(), self._ui.boundary.text(), ExtrudeModel.PLANE,
                              thickness=self._ui.thickness.text())

    def _connectSignalsSlots(self):
        self._ui.projectName.textChanged.connect(self._updateProjectLocation)
        self._ui.locationSelect.clicked.connect(self._selectLocation)
        self._ui.boundarySelect.clicked.connect(self._selectBoundary)
        self._ui.ok.clicked.connect(self._accept)

    def _selectLocation(self):
        self._dialog = QFileDialog(self, self.tr('Select Location'), str(self._baseLocation))
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._locationParentSelected)
        self._dialog.open()

    def _updateProjectLocation(self):
        self._ui.projectLocation.setText(str(self._baseLocation / self._ui.projectName.text()))

    def _locationParentSelected(self, dir):
        self._baseLocation = Path(dir).resolve()
        self._updateProjectLocation()

    def _selectBoundary(self):
        self._dialog = self._createBoundarySelector()
        self._dialog.accepted.connect(lambda: self._ui.boundary.setText(self._dialog.selectedText()))
        self._dialog.open()

    def _createBoundarySelector(self):
        items = []
        for gId, geometry in app.db.getElements(
                'geometry', lambda i, e: e['cfdType'] == CFDType.BOUNDARY.value).items():
            name = geometry.value('name')
            items.append(SelectorItem(name, name, gId))

        return SelectorDialog(self, self.tr('Select Boundary'), self.tr('Select Boundary'), items)

    @qasync.asyncSlot()
    async def _accept(self):
        if not self._ui.projectName.text().strip():
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Enter Project Name'))
            return

        if not self._baseLocation.exists():
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr(f'{self._baseLocation} is not a directory.'))
            return

        if Path(self._ui.projectLocation.text()).exists():
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr(f'{self._ui.projectLocation.text()} already exists.'))
            return

        if not self._ui.boundary.text():
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Boundary'))
            return

        try:
            float(self._ui.thickness.text())
        except ValueError:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Thickness must be a float'))
            return

        super().accept()