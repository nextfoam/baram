#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from random import random
from uuid import UUID

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

import qasync
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.visual_report import VisualReport
from baramFlow.mesh.mesh_model import DisplayMode

from baramFlow.view.results.visual_reports.openfoam_reader import OpenFOAMReader
from baramFlow.view.widgets.rendering_view import RenderingView
from widgets.overlay_frame import OverlayFrame

from .display_control.display_control import DisplayControl

@dataclass
class ScaffoldDisplayItem:
    scaffold: UUID
    displayItem: UUID

class VisualReportView(RenderingView):
    actorPicked = Signal(vtkActor, bool)
    renderingModeChanged = Signal(DisplayMode)
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None, report: VisualReport = None):
        super().__init__(parent)

        self._overlayFrame = OverlayFrame(self._view)
        self._displayControl = DisplayControl(self._overlayFrame, self._view)
        layout = QVBoxLayout(self._overlayFrame)
        layout.addWidget(self._displayControl)
        self._overlayFrame.adjustSize()

        self._report = report

        self._scaffolds: dict[UUID, UUID] = {}
        self._updatedScaffolds: set[UUID] = set()

        self._timer = QTimer()
        self._timer.setInterval(200*(1+random()))  # "random" is introduced to distribute the execution
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._refresh)

        for s in ScaffoldsDB().getScaffolds().values():
            self._updatedScaffolds.add(s.uuid)

        self._timer.start()

    def _connectSignalsSlots(self):
        super()._connectSignalsSlots()

        ScaffoldsDB().ScaffoldAdded.connect(self._scaffoldUpdated)
        ScaffoldsDB().ScaffoldUpdated.connect(self._scaffoldUpdated)
        ScaffoldsDB().RemovingScaffold.connect(self._scaffoldUpdated)

    def _disconnectSignalsSlots(self):
        ScaffoldsDB().ScaffoldAdded.disconnect(self._scaffoldUpdated)
        ScaffoldsDB().ScaffoldUpdated.disconnect(self._scaffoldUpdated)
        ScaffoldsDB().RemovingScaffold.disconnect(self._scaffoldUpdated)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlayFrame.updateGeometry()

    def closeEvent(self, event):
        self._disconnectSignalsSlots()

        super().closeEvent(event)

    @qasync.asyncSlot()
    async def _scaffoldUpdated(self, uuid: UUID):
        self._updatedScaffolds.add(uuid)

        self._timer.start()

    @qasync.asyncSlot()
    async def _refresh(self):
        if len(self._updatedScaffolds) == 0:
            return

        with OpenFOAMReader() as reader:
            reader.setTimeValue(float(self._report.time))
            while len(self._updatedScaffolds) > 0:
                uuid = self._updatedScaffolds.pop()
                mBlock = reader.getOutput()
                if ScaffoldsDB().hasScaffold(uuid):
                    scaffold = ScaffoldsDB().getScaffold(uuid)
                    dataset = scaffold.getDataSet(mBlock)
                    if uuid in self._scaffolds:
                        id_ = self._scaffolds[uuid]
                        self._displayControl.update(id_, scaffold.name, dataset)
                    else:
                        id_ = self._displayControl.add(scaffold.name, dataset)
                        self._scaffolds[uuid] = id_
                else:
                    if uuid in self._scaffolds:
                        id_ = self._scaffolds[uuid]
                        self._displayControl.remove(id_)

                        del self._scaffolds[uuid]

        self._view.refresh()

