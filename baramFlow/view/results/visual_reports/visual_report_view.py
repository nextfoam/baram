#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

import matplotlib as mpl

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeWidget, QWidget, QVBoxLayout

import qasync
from vtkmodules.vtkCommonCore import vtkLookupTable, vtkScalarsToColors
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.app import app

from baramFlow.coredb.contour import Contour
from baramFlow.coredb.post_field import FieldType, VectorComponent
from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.visual_report import VisualReport

from baramFlow.view.results.visual_reports.display_control.colormap.colormap import colormapData
from baramFlow.view.results.visual_reports.display_control.contour_colormap_dialog import ContourColormapDialog
from baramFlow.view.results.visual_reports.display_control.display_context_menu import DisplayContextMenu
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

        self._scaffoldTreeWidget = QTreeWidget(self._overlayFrame)
        self._scaffoldTreeWidget.headerItem().setText(2, "")
        self._scaffoldTreeWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._scaffoldTreeWidget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._scaffoldTreeWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._scaffoldTreeWidget.setSortingEnabled(True)
        self._scaffoldTreeWidget.setColumnCount(3)
        self._scaffoldTreeWidget.header().setVisible(True)
        self._scaffoldTreeWidget.header().setStretchLastSection(False)

        layout = QVBoxLayout(self._overlayFrame)
        layout.addWidget(self._scaffoldTreeWidget)

        self._overlayFrame.adjustSize()

        self._menu = DisplayContextMenu(self._scaffoldTreeWidget)

        self._items: dict[UUID, DisplayItem] = {}
        self._selectedItems: list[DisplayItem] = []

        self._scaffoldTreeWidget.setColumnWidth(Column.COLOR_COLUMN, 20)

        self._scaffoldTreeWidget.header().setSectionResizeMode(Column.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        self._scaffoldTreeWidget.header().setSectionResizeMode(Column.TYPE_COLUMN, QHeaderView.ResizeMode.ResizeToContents)

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

        self._initLatterTask = asyncio.create_task(self._registerReportingScaffolds())

        contour: Contour = report
        contour.rangeMin, contour.rangeMax = contour.getValueRange(contour.useNodeValues, contour.relevantScaffoldsOnly)

        self._updateLookupTable()

        self._connectSignalsSlots()

    async def _registerReportingScaffolds(self):
        for rs in self._report.reportingScaffolds.values():

            displayUuid = self._addItem(rs)

            self._scaffold2displayItem[rs.scaffoldUuid] = displayUuid

        self._view.fitCamera()

        self._view.refresh()

    def _connectSignalsSlots(self):
        self._scaffoldTreeWidget.customContextMenuRequested.connect(self._showContextMenu)
        self._scaffoldTreeWidget.itemSelectionChanged.connect(self._selectedItemsChanged)
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
        self._menu.streamsToggled.connect(self._streamsToggled)

        ScaffoldsDB().ScaffoldUpdated.connect(self._scaffoldUpdated)

        self._report.instanceUpdated.connect(self._reportUpdated)
        self._report.reportingScaffoldAdded.connect(self._reportingScaffoldAdded)
        self._report.reportingScaffoldRemoving.connect(self._reportingScaffoldRemoving)

    def _disconnectSignalsSlots(self):
        ScaffoldsDB().ScaffoldUpdated.disconnect(self._scaffoldUpdated)

        self._report.instanceUpdated.disconnect(self._reportUpdated)
        self._report.reportingScaffoldAdded.disconnect(self._reportingScaffoldAdded)
        self._report.reportingScaffoldRemoving.disconnect(self._reportingScaffoldRemoving)

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
        scaffold = ScaffoldsDB().getScaffold(uuid)
        dataSet = await scaffold.getDataSet(self._report.polyMesh)
        self._report.reportingScaffolds[uuid].dataSet = dataSet

        displayUuid = self._scaffold2displayItem[uuid]
        item = self._items[displayUuid]

        await item.updateScaffoldInfo()

        self._view.refresh()


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
        self._executeContextMenu(self._scaffoldTreeWidget.mapToGlobal(pos))

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
        items = self._scaffoldTreeWidget.selectedItems()
        if not items:
            return None

        self._selectedItems.clear()
        baseProp: Properties = items[0].properties()
        properties = Properties(baseProp.visibility,
                                baseProp.opacity,
                                baseProp.color,
                                baseProp.colorMode,
                                baseProp.displayMode,
                                baseProp.showVectors,
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
            self._scaffoldTreeWidget.clearSelection()

        if actor:
            print(f'{actor.GetObjectName()} picked')
            item = self._items[UUID(actor.GetObjectName())]
            if not item.isSelected() and forContextMenu:
                self._scaffoldTreeWidget.clearSelection()

            if ctrlKeyPressed:
                item.setSelected(not item.isSelected())
            else:
                item.setSelected(True)

    def _actorSourceUpdated(self, id_):
        pass

    @qasync.asyncSlot()
    async def _vectorsToggled(self, checked: bool):
        for item in self._selectedItems:
            if checked:
                await item.showVectors()
            else:
                item.hideVectors()

        self._view.refresh()

    def _streamsToggled(self, checked: bool):
        for item in self._selectedItems:
            if checked:
                item.showStreamlines()
            else:
                item.hideStreamlines()

        self._view.refresh()

    def _addItem(self, rs: ReportingScaffold) -> UUID:
        did = uuid4()
        contour: Contour = self._report

        item = DisplayItem(self._scaffoldTreeWidget, did, rs, contour.internalMesh, contour.field, contour.useNodeValues, self._lookupTable, self._view)

        self._items[did] = item

        item.setupColorWidget(self._scaffoldTreeWidget)

        return did

    def removeItem(self, did: UUID):
        if did not in self._items:
            return

        for i in range(self._scaffoldTreeWidget.topLevelItemCount()):
            item: DisplayItem = self._scaffoldTreeWidget.topLevelItem(i)
            if item.did() != did:
                continue

            self._scaffoldTreeWidget.takeTopLevelItem(i)

            item.close()

            del self._items[did]
            del item

            break

    def _reportingScaffoldAdded(self, uuid: UUID):
        rs = self._report.reportingScaffolds[uuid]
        displayUuid = self._addItem(rs)

        self._scaffold2displayItem[uuid] = displayUuid

        self._view.refresh()

    def _reportingScaffoldRemoving(self, uuid: UUID):
        displayUuid = self._scaffold2displayItem[uuid]
        self.removeItem(displayUuid)

        del self._scaffold2displayItem[uuid]

        self._view.refresh()
