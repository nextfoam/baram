#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog, QFileDialog, QWidget, QVBoxLayout

from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog, SelectorItem

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType
from baramMesh.openfoam.system.extrude_mesh_dict import ExtrudeOptions, ExtrudeModel
from .export_2D_wedge_dialog_ui import Ui_Export2DWedgeDialog
from .export_2D_region_widgets import Export2DWedgeRegionWidget


class Export2DWedgeDialog(QDialog):
    def __init__(self, parent, path=None):
        super().__init__(parent)

        self._ui = Ui_Export2DWedgeDialog()
        self._ui.setupUi(self)

        self._regionWidgets = []
        
        self._boundaries = []
        self._dialog = None

        regionsWidget = QWidget()        
        self._ui.parameters.layout().insertWidget(0, regionsWidget)

        layout = QVBoxLayout(regionsWidget)
        layout.setContentsMargins(0, -1, 0, 0)
        
        for region in app.db.getElements('region').values():
            widget = Export2DWedgeRegionWidget(region.value('name'))
            widget.p1SelectClicked.connect(self._openBoundarySelectorDialog)
            widget.p2SelectClicked.connect(self._openBoundarySelectorDialog)
            layout.addWidget(widget)
            self._regionWidgets.append(widget)

        self._baseLocation = Path.home() if path is None else path
        self._updateProjectLocation()

        for gId, geometry in app.db.getElements(
                'geometry', lambda i, e: e['cfdType'] == CFDType.BOUNDARY.value).items():
            name = geometry.value('name')
            self._boundaries.append(SelectorItem(name, name, gId))

        self._connectSignalsSlots()

    def projectLocation(self):
        return Path(self._ui.projectLocation.text())

    def extrudeOptions(self):
        return ([(b.rname(), b.p1(), b.p2()) for b in self._regionWidgets], 
                ExtrudeOptions(ExtrudeModel.WEDGE,
                               point=[self._ui.originX.text(), self._ui.originY.text(), self._ui.originZ.text()],
                               axis=[self._ui.directionX.text(), self._ui.directionY.text(), self._ui.directionZ.text()],
                               angle=self._ui.angle.text()))
        # return ExtrudeOptions(self._ui.p1.text(), self._ui.p2.text(), ExtrudeModel.WEDGE,
        #                       point=[self._ui.originX.text(), self._ui.originY.text(), self._ui.originZ.text()],
        #                       axis=[self._ui.directionX.text(), self._ui.directionY.text(), self._ui.directionZ.text()],
        #                       angle=self._ui.angle.text())

    def _connectSignalsSlots(self):
        self._ui.projectName.textChanged.connect(self._updateProjectLocation)
        self._ui.locationSelect.clicked.connect(self._selectLocation)
        # self._ui.p1Select.clicked.connect(self._selectP1)
        # self._ui.p2Select.clicked.connect(self._selectP2)
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

    def _openBoundarySelectorDialog(self, widget):
        self._dialog = self._createBoundarySelector()
        self._dialog.accepted.connect(lambda: widget.setText(self._dialog.selectedText()))
        self._dialog.open()

    # def _selectP1(self):
    #     self._dialog = self._createBoundarySelector()
    #     self._dialog.accepted.connect(lambda: self._ui.p1.setText(self._dialog.selectedText()))
    #     self._dialog.open()

    # def _selectP2(self):
    #     self._dialog = self._createBoundarySelector()
    #     self._dialog.accepted.connect(lambda: self._ui.p2.setText(self._dialog.selectedText()))
    #     self._dialog.open()

    def _createBoundarySelector(self):
        return SelectorDialog(self, self.tr('Select Boundary'), self.tr('Select Boundary'), self._boundaries)

    @qasync.asyncSlot()
    async def _accept(self):
        def validateFloat(value, label):
            nonlocal currentItem
            currentItem = label
            float(value)

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

        for widget in self._regionWidgets:
            if not widget.p1():
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'), self.tr('Select P1 - ' + widget.rname()))
                return

            if not widget.p2():
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'), self.tr('Select P2 - ' + widget.rname()))
                return

        currentItem = None
        try:
            validateFloat(self._ui.angle.text(), self.tr('Angle'))
            validateFloat(self._ui.originX.text(), self.tr('Oring X'))
            validateFloat(self._ui.originY.text(), self.tr('Oring Y'))
            validateFloat(self._ui.originZ.text(), self.tr('Oring Z'))
        except ValueError:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('{} must be a float').format(currentItem))
            return

        super().accept()