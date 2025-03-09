#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from random import random
from uuid import UUID

import matplotlib as mpl

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

import qasync
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.coredb.contour import Contour
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.visual_report import VisualReport

from baramFlow.view.results.visual_reports.display_control.colormap.colormap import colormapData
from baramFlow.view.results.visual_reports.display_control.contour_colormap_dialog import ContourColormapDialog
from baramFlow.view.results.visual_reports.openfoam_reader import OpenFOAMReader
from baramFlow.view.results.visual_reports.scalar_bar_widget import ScalarBarWidget
from baramFlow.view.widgets.rendering_view import RenderingView

from libbaram.colormap import sequentialRedLut

from widgets.overlay_frame import OverlayFrame

from .display_control.display_control import DisplayControl

@dataclass
class ScaffoldDisplayItem:
    scaffold: UUID
    displayItem: UUID


class VisualReportView(RenderingView):
    actorPicked = Signal(vtkActor, bool)
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None, report: VisualReport = None):
        super().__init__(parent)

        layout = self._ui.renderingMode.parentWidget().layout()
        layout.removeWidget(self._ui.renderingMode)
        self._ui.renderingMode.setParent(None)
        self._ui.renderingMode = None

        self._dialog = None

        self._lookupTable = vtkLookupTable()

        self._overlayFrame = OverlayFrame(self._view)
        self._displayControl = DisplayControl(self._overlayFrame, self._view, self._lookupTable)
        layout = QVBoxLayout(self._overlayFrame)
        layout.addWidget(self._displayControl)
        self._overlayFrame.adjustSize()

        self._colormap = ScalarBarWidget(self, report, self._colormapDoubleClicked)
        self._colormap.SetInteractor(self._view.interactor())

        actor: vtkScalarBarActor = self._colormap.GetScalarBarActor()
        actor.SetLookupTable(self._lookupTable)
        actor.UnconstrainedFontSizeOn()

        representation = self._colormap.GetScalarBarRepresentation()
        representation.SetPosition(0.03, 0.03)
        representation.SetPosition2(0.08, 0.33)

        self._colormap.On()

        self._report = report

        self._scaffold2displayItem: dict[UUID, UUID] = {}
        self._updatedScaffolds: set[UUID] = set()

        #  "random" is introduced to distribute the execution
        self._timer = QTimer()
        self._timer.setInterval(200*(1+random()))
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._refresh)

        for s in ScaffoldsDB().getScaffolds().values():
            self._updatedScaffolds.add(s.uuid)

        self._refresh()

        contour: Contour = report
        contour.rangeMin, contour.rangeMax = self._displayControl.getValueRange(contour.field,
                                                        contour.vectorComponent,
                                                        contour.useNodeValues,
                                                        contour.relevantScaffoldsOnly)
        self._updateLookupTable()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        ScaffoldsDB().ScaffoldAdded.connect(self._scaffoldUpdated)
        ScaffoldsDB().ScaffoldUpdated.connect(self._scaffoldUpdated)
        ScaffoldsDB().RemovingScaffold.connect(self._scaffoldUpdated)

        self._report.instanceUpdated.connect(self._reportUpdated)

    def _disconnectSignalsSlots(self):
        ScaffoldsDB().ScaffoldAdded.disconnect(self._scaffoldUpdated)
        ScaffoldsDB().ScaffoldUpdated.disconnect(self._scaffoldUpdated)
        ScaffoldsDB().RemovingScaffold.disconnect(self._scaffoldUpdated)

        self._report.instanceUpdated.disconnect(self._reportUpdated)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlayFrame.updateGeometry()

    def closeEvent(self, event):
        self._disconnectSignalsSlots()

        super().closeEvent(event)

    def _colormapDoubleClicked(self):
        self._dialog = ContourColormapDialog(self, self._report, self._displayControl)
        self._dialog.accepted.connect(self._updateLookupTable)
        self._dialog.open()

    def _updateLookupTable(self):
        contour: Contour = self._report

        self._lookupTable.SetNumberOfTableValues(contour.numberOfLevels)

        if contour.useCustomColorScheme:
            self._lookupTable.SetHueRange(contour.customMinColor.hueF(), contour.customMaxColor.hueF())
            self._lookupTable.SetSaturationRange(contour.customMinColor.saturationF(), contour.customMaxColor.saturationF())
            self._lookupTable.SetValueRange(contour.customMinColor.valueF(), contour.customMaxColor.valueF())
            self._lookupTable.Build()
        else:
            levels = contour.numberOfLevels
            # cmap = mpl.colormaps['viridis']

            # for i in range(0, STEP):
            #     rgb = cmap(i/(STEP-1))[:3]  # Extract RGB values excluding Alpha
            #     lut.SetTableValue(i, *rgb)

            cmap = colormapData(contour.colorScheme)
            for i in range(0, levels):
                rgb = cmap[i * 255 // ( levels - 1)]
                self._lookupTable.SetTableValue(i, *rgb)

        self._lookupTable.SetAboveRangeColor(0, 0, 0, 0)  # Transparent
        self._lookupTable.SetBelowRangeColor(0, 0, 0, 0)  # Transparent

        if contour.useCustomRange:
            self._lookupTable.SetTableRange(float(contour.customRangeMin), float(contour.customRangeMax))
        else:
            self._lookupTable.SetTableRange(contour.rangeMin, contour.rangeMax)

        if contour.clipToRange:
            self._lookupTable.UseAboveRangeColorOn()
            self._lookupTable.UseBelowRangeColorOn()
        else:
            self._lookupTable.UseAboveRangeColorOff()
            self._lookupTable.UseBelowRangeColorOff()

        self._lookupTable.Build()
        self._view.refresh()

    @qasync.asyncSlot()
    async def _scaffoldUpdated(self, uuid: UUID):
        self._updatedScaffolds.add(uuid)

        self._timer.start()

    def _reportUpdated(self, uuid: UUID):
        self._updatedScaffolds.update(list(self._scaffold2displayItem))
        self._timer.start()

    def _refresh(self):
        if len(self._updatedScaffolds) == 0:
            return

        with OpenFOAMReader() as reader:
            reader.setTimeValue(float(self._report.time))
            reader.Update()
            print(f'OF Time {self._report.time}')
            while len(self._updatedScaffolds) > 0:
                uuid = self._updatedScaffolds.pop()
                mBlock = reader.getOutput()
                if ScaffoldsDB().hasScaffold(uuid):
                    scaffold = ScaffoldsDB().getScaffold(uuid)
                    dataset = scaffold.getDataSet(mBlock)
                    if uuid in self._scaffold2displayItem:
                        displayUuid = self._scaffold2displayItem[uuid]
                        self._displayControl.updateItem(displayUuid, scaffold.name, dataset)
                    else:
                        displayUuid = self._displayControl.addItem(scaffold.name, dataset)
                        self._scaffold2displayItem[uuid] = displayUuid
                else:
                    if uuid in self._scaffold2displayItem:
                        displayUuid = self._scaffold2displayItem[uuid]
                        self._displayControl.removeItem(displayUuid)

                        del self._scaffold2displayItem[uuid]

        self._view.refresh()

