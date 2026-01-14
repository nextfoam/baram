#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout

from widgets.async_message_box import AsyncMessageBox
from widgets.new_project_widget import NewProjectWidget
from widgets.selector_dialog import SelectorDialog, SelectorItem

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType
from baramMesh.openfoam.system.extrude_mesh_dict import ExtrudeOptions, ExtrudeModel
from .export_2D_plane_dialog_ui import Ui_Export2DPlaneDialog
from .export_2D_region_widgets import Export2DPlaneRegionWidget


class Export2DPlaneDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_Export2DPlaneDialog()
        self._ui.setupUi(self)

        self._pathWidget = NewProjectWidget(self._ui.path, suffix=app.properties.exportSuffix)

        self._regionWidgets = []

        self._boundaries = []
        self._dialog = None

        layout = QVBoxLayout(self._ui.path)
        layout.addWidget(self._pathWidget)
        self._pathWidget.hideValidationMessage()

        regionsWidget = QWidget()
        self._ui.parameters.layout().insertWidget(0, regionsWidget)

        layout = QVBoxLayout(regionsWidget)
        layout.setContentsMargins(0, -1, 0, 0)

        for region in app.db.getElements('region').values():
            widget = Export2DPlaneRegionWidget(region.value('name'))
            widget.boundarySelectClicked.connect(self._openBoundarySelectorDialog)
            layout.addWidget(widget)
            self._regionWidgets.append(widget)

        for gId, geometry in app.db.getElements(
                'geometry', lambda i, e: e['cfdType'] == CFDType.BOUNDARY.value).items():
            name = geometry.value('name')
            self._boundaries.append(SelectorItem(name, name, gId))

        self._connectSignalsSlots()

    def projectPath(self):
        return self._pathWidget.projectPath()

    def isRunBaramFlowChecked(self):
        return self._ui.run.isChecked()

    def extrudeOptions(self):
        return ([(b.rname(), b.boundary(), b.boundary()) for b in self._regionWidgets],
                ExtrudeOptions(ExtrudeModel.PLANE, thickness=self._ui.thickness.text()))

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    def _openBoundarySelectorDialog(self, widget):
        self._dialog = self._createBoundarySelector()
        self._dialog.accepted.connect(lambda: widget.setText(self._dialog.selectedText()))
        self._dialog.open()

    def _createBoundarySelector(self):
        return SelectorDialog(self, self.tr('Select Boundary'), self.tr('Select Boundary'), self._boundaries)

    @qasync.asyncSlot()
    async def _accept(self):
        path = self._pathWidget.projectPath()
        if path is None:
            if self._pathWidget.validationMessage():
                await AsyncMessageBox().information(self, self.tr('Input Error'), self._pathWidget.validationMessage())
                return
            else:
                await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Enter Project Name'))
                return

        for widget in self._regionWidgets:
            if not widget.boundary():
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'), self.tr('Select Boundary - ' + widget.rname()))
                return

        try:
            self._ui.thickness.validate(self.tr('Thickness'))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        super().accept()