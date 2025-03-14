#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import Field, dataclass
from random import random
import sys
from typing import Optional
from uuid import UUID, uuid4

import matplotlib as mpl

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeWidget, QWidget, QVBoxLayout

import qasync
from vtkmodules.vtkCommonCore import vtkLookupTable, vtkScalarsToColors
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.app import app

from baramFlow.coredb.contour import Contour
from baramFlow.coredb.post_field import FieldType, VectorComponent
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.visual_report import VisualReport

from baramFlow.view.results.visual_reports.display_control.colormap.colormap import colormapData
from baramFlow.view.results.visual_reports.display_control.contour_colormap_dialog import ContourColormapDialog
from baramFlow.view.results.visual_reports.display_control.display_context_menu import DisplayContextMenu
from baramFlow.view.results.visual_reports.openfoam_reader import OpenFOAMReader
from baramFlow.view.results.visual_reports.scalar_bar_widget import ScalarBarWidget
from baramFlow.view.widgets.rendering_view import RenderingView

from widgets.overlay_frame import OverlayFrame

from baramFlow.view.results.visual_reports.display_control.display_item import ColorMode, DisplayMode, Properties, DisplayItem, Column


@dataclass
class ScaffoldDisplayItem:
    selectedActorsChanged = Signal(list)
    selectionApplied = Signal()
    scaffold: UUID
    displayItem: UUID


class VisualReportView(RenderingView):
    actorPicked = Signal(vtkActor, bool)
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None, report: VisualReport = None):
        super().__init__(parent)

        # Remove RenderingMode tool menu, which is not used in Visual Report
        layout = self._ui.renderingMode.parentWidget().layout()
        layout.removeWidget(self._ui.renderingMode)
        self._ui.renderingMode.setParent(None)
        self._ui.renderingMode = None

        self._dialog = None

        self._lookupTable = vtkLookupTable()

        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._overlayFrame = OverlayFrame(self._view)

        self._scaffoldList = QTreeWidget(self._overlayFrame)
        self._scaffoldList.headerItem().setText(2, "")
        self._scaffoldList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._scaffoldList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._scaffoldList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._scaffoldList.setSortingEnabled(True)
        self._scaffoldList.setColumnCount(3)
        self._scaffoldList.header().setVisible(True)
        self._scaffoldList.header().setStretchLastSection(False)

        layout = QVBoxLayout(self._overlayFrame)
        layout.addWidget(self._scaffoldList)

        self._overlayFrame.adjustSize()

        self._menu = DisplayContextMenu(self._scaffoldList)

        self._items: dict[UUID, DisplayItem] = {}
        self._selectedItems: list[DisplayItem] = []

        self._scaffoldList.setColumnWidth(Column.COLOR_COLUMN, 20)

        self._scaffoldList.header().setSectionResizeMode(Column.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        self._scaffoldList.header().setSectionResizeMode(Column.TYPE_COLUMN, QHeaderView.ResizeMode.ResizeToContents)

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
        contour.rangeMin, contour.rangeMax = self.getValueRange(contour.field,
                                                        contour.fieldComponent,
                                                        contour.useNodeValues,
                                                        contour.relevantScaffoldsOnly)
        self._updateLookupTable()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._scaffoldList.customContextMenuRequested.connect(self._showContextMenu)
        self._scaffoldList.itemSelectionChanged.connect(self._selectedItemsChanged)
        self._view.customContextMenuRequested.connect(self._showContextMenuOnRenderingView)
        self._view.actorPicked.connect(self._actorPicked)
        self._menu.showActionTriggered.connect(self._showActors)
        self._menu.hideActionTriggered.connect(self._hideActors)
        self._menu.opacitySelected.connect(self._applyOpacity)
        self._menu.colorPicked.connect(self._applyColor)
        self._menu.solidColorModeSelected.connect(self._solidColorMode)
        self._menu.fieldColorModeSelected.connect(self._fieldColorMode)
        self._menu.wireframeDisplayModeSelected.connect(self._displayWireframe)
        self._menu.surfaceDisplayModeSelected.connect(self._displaySurface)
        self._menu.surfaceEdgeDisplayModeSelected.connect(self._displayWireSurfaceWithEdges)
        self._menu.vectorsToggled.connect(self._vectorsToggled)

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
        self._dialog = ContourColormapDialog(self, self._report)
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
        contour: Contour = self._report

        if contour.field.type == FieldType.VECTOR:
            if contour.fieldComponent == VectorComponent.MAGNITUDE:
                if self._lookupTable.GetVectorMode() != vtkScalarsToColors.MAGNITUDE:
                    self._lookupTable.SetVectorMode(vtkScalarsToColors.MAGNITUDE)
            else:
                if self._lookupTable.GetVectorMode() != vtkScalarsToColors.COMPONENT:
                    self._lookupTable.SetVectorMode(vtkScalarsToColors.COMPONENT)

                if contour.fieldComponent == VectorComponent.X:
                    if self._lookupTable.GetVectorComponent() != 0:
                        self._lookupTable.SetVectorComponent(0)
                elif contour.fieldComponent == VectorComponent.Y:
                    if self._lookupTable.GetVectorComponent() != 1:
                        self._lookupTable.SetVectorComponent(1)
                elif contour.fieldComponent == VectorComponent.Z:
                    if self._lookupTable.GetVectorComponent() != 2:
                        self._lookupTable.SetVectorComponent(2)

        for did in self._items:
            item = self._items[did]
            item.setField(contour.field, contour.useNodeValues)

        self._view.refresh()

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
                        self.updateItemScaffold(displayUuid, scaffold.name, dataset)
                    else:
                        displayUuid = self.addItem(scaffold.name, scaffold.uuid, dataset)
                        self._scaffold2displayItem[uuid] = displayUuid
                else:
                    if uuid in self._scaffold2displayItem:
                        displayUuid = self._scaffold2displayItem[uuid]
                        self.removeItem(displayUuid)

                        del self._scaffold2displayItem[uuid]

        self._view.refresh()


    def getValueRange(self, field: Field, vectorComponent: VectorComponent, useNodeValues: bool, relevantScaffoldsOnly: bool) -> tuple[float, float]:
        rMin = sys.float_info.max
        rMax = sys.float_info.min

        for item in self._items.values():
            if relevantScaffoldsOnly:
                if  not item.isActorVisible() or item.colorMode() == ColorMode.SOLID:
                    continue

            if field.type == FieldType.VECTOR:
                valueRange = item.getVectorRange(field, vectorComponent, useNodeValues)
            else:
                valueRange = item.getScalarRange(field, useNodeValues)

            rMin = min(rMin, valueRange[0])
            rMax = max(rMax, valueRange[1])

        return rMin, rMax

    def _selectedItemsChanged(self):
        ids = []
        for item in self._items.values():
            item.setHighlighted(item.isSelected())
            if item.isSelected():
                ids.append(item.did())

        self._view.refresh()

    def _executeContextMenu(self, pos):
        properties = self._selectedItemsInfo()
        if properties is None:
            return

        self._menu.execute(pos, properties)

    def _showContextMenu(self, pos):
        self._executeContextMenu(self._scaffoldList.mapToGlobal(pos))

    def _showContextMenuOnRenderingView(self, pos):
        #  VTK ignores device pixel ratio and uses real pixel values only
        ratio = app.qApplication.primaryScreen().devicePixelRatio()
        x = pos.x() * ratio
        y = (self._view.height() - pos.y() - 1) * ratio
        actor = self._view.pickActor(x, y)
        if actor:
            self._actorPicked(actor, False, True)
            self._executeContextMenu(self._view.mapToGlobal(pos))

    def _selectedItemsInfo(self) -> Optional[Properties]:
        items = self._scaffoldList.selectedItems()
        if not items:
            return None

        self._selectedItems.clear()
        baseProp: Properties = items[0].properties()
        properties = Properties(baseProp.visibility,
                                baseProp.opacity,
                                baseProp.color,
                                baseProp.colorMode,
                                baseProp.displayMode,
                                baseProp.highlighted)

        for item in items:
            self._selectedItems.append(item)
            properties.merge(item.properties())

        return properties

    def _showActors(self):
        for item in self._selectedItems:
            item.setActorVisible(True)

        self._view.refresh()

    def _hideActors(self):
        for item in self._selectedItems:
            item.setActorVisible(False)

        self._view.refresh()

    def _displayWireframe(self):
        for item in self._selectedItems:
            item.setDisplayMode(DisplayMode.WIREFRAME)

        self._view.refresh()

    def _displaySurface(self):
        for item in self._selectedItems:
            item.setDisplayMode(DisplayMode.SURFACE)

        self._view.refresh()

    def _displayWireSurfaceWithEdges(self):
        for item in self._selectedItems:
            item.setDisplayMode(DisplayMode.SURFACE_EDGE)

        self._view.refresh()

    def _applyOpacity(self, opacity):
        for item in self._selectedItems:
            item.setOpacity(opacity)

    def _applyColor(self, color):
        for item in self._selectedItems:
            item.setActorColor(color)

    def _solidColorMode(self):
        for item in self._selectedItems:
            item.setColorMode(ColorMode.SOLID)

        self._view.refresh()

    def _fieldColorMode(self):
        for item in self._selectedItems:
            item.setColorMode(ColorMode.FIELD)

        self._view.refresh()

    def _actorPicked(self, actor: vtkActor, ctrlKeyPressed=False, forContextMenu=False):
        if not ctrlKeyPressed and not forContextMenu:
            self._scaffoldList.clearSelection()

        if actor:
            print(f'{actor.GetObjectName()} picked')
            item = self._items[UUID(actor.GetObjectName())]
            if not item.isSelected() and forContextMenu:
                self._scaffoldList.clearSelection()

            if ctrlKeyPressed:
                item.setSelected(not item.isSelected())
            else:
                item.setSelected(True)

    def _actorSourceUpdated(self, id_):
        pass

    def _vectorsToggled(self, checked: bool):
        for item in self._selectedItems:
            if checked:
                item.showVectors()
            else:
                item.hideVectors()

        self._view.refresh()

    def addItem(self, name: str, scaffold: UUID, dataSet) -> UUID:
        did = uuid4()
        contour: Contour = self._report
        item = DisplayItem(self._scaffoldList, did, name, scaffold, dataSet, contour.field, contour.useNodeValues, self._lookupTable, self._view)

        self._items[did] = item

        item.setupColorWidget(self._scaffoldList)

        return did

    def removeItem(self, did: UUID):
        if did not in self._items:
            return

        for i in range(self._scaffoldList.topLevelItemCount()):
            item: DisplayItem = self._scaffoldList.topLevelItem(i)
            if item.did() != did:
                continue

            self._scaffoldList.takeTopLevelItem(i)

            item.close()

            del self._items[did]
            del item

            break

    def updateItemScaffold(self, did: UUID, name: str, dataSet) -> UUID:
        if did not in self._items:
            return

        item = self._items[did]
        item.setName(name)
        item.setDataSet(dataSet)