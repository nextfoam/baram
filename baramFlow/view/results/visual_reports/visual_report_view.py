#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from uuid import UUID, uuid4

from PySide6.QtGui import QAction
import matplotlib as mpl

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QColorDialog, QHeaderView, QMenu, QTreeWidget, QWidget, QVBoxLayout

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
from baramFlow.view.results.visual_reports.display_control.opacity_dialog import OpacityDialog
from baramFlow.view.results.visual_reports.display_control.reporting_scaffold_dialog import ReportingScaffoldDialog
from baramFlow.view.results.visual_reports.scalar_bar_widget import ScalarBarWidget
from baramFlow.view.widgets.rendering_view import RenderingView

from widgets.overlay_frame import OverlayFrame

from baramFlow.view.results.visual_reports.display_control.display_item import ColorMode, DisplayMode, DisplayItem, Column


class VisualReportView(RenderingView):
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

        self._menu = QMenu(self._scaffoldTreeWidget)
        self._setUpContextMenu(self._menu)

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

        self._opacityDialog.accepted.connect(self._opacityChanged)
        self._colorDialog.accepted.connect(self._colorChanged)

        ScaffoldsDB().scaffoldUpdated.asyncConnect(self._scaffoldUpdated)

        self._report.instanceUpdated.asyncConnect(self._reportUpdated)
        self._report.reportingScaffoldAdded.asyncConnect(self._reportingScaffoldAdded)
        self._report.reportingScaffoldRemoving.asyncConnect(self._reportingScaffoldRemoving)

    def _disconnectSignalsSlots(self):
        ScaffoldsDB().scaffoldUpdated.disconnect(self._scaffoldUpdated)

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

    async def _scaffoldUpdated(self, uuid: UUID):
        scaffold = ScaffoldsDB().getScaffold(uuid)
        dataSet = await scaffold.getDataSet(self._report.polyMesh)
        self._report.reportingScaffolds[uuid].dataSet = dataSet

        displayUuid = self._scaffold2displayItem[uuid]
        item = self._items[displayUuid]

        await item.updateScaffoldInfo()

        self._view.refresh()


    async def _reportUpdated(self, uuid: UUID):
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
            await item.updateScaffoldInfo()

        self._view.refresh()

    def _selectedItemsChanged(self):
        ids = []
        for item in self._items.values():
            item.setHighlighted(item.isSelected())
            if item.isSelected():
                ids.append(item.did())

        self._view.refresh()

    def _executeContextMenu(self, pos):
        items: list[DisplayItem] = self._scaffoldTreeWidget.selectedItems()
        if len(items) == 0:
            return

        self._selectedItems = items

        self._showAction.setVisible(not all([item.visibility for item in items]))
        self._hideAction.setVisible(not all([not item.visibility for item in items]))

        self._colorAction.setEnabled(not all([item.colorMode == ColorMode.FIELD for item in items]))

        self._solidColorAction.setChecked(all([item.colorMode == ColorMode.SOLID for item in items]))
        self._fieldColorAction.setChecked(all([item.colorMode == ColorMode.FIELD for item in items]))

        self._wireFrameDisplayAction.setChecked(all([item.displayMode == DisplayMode.WIREFRAME for item in items]))
        self._surfaceDisplayAction.setChecked(all([item.displayMode == DisplayMode.SURFACE for item in items]))
        self._surfaceEdgeDisplayAction.setChecked(all([item.displayMode == DisplayMode.SURFACE_EDGE for item in items]))

        self._showVectorsAction.setVisible(not all([item.showVectors for item in items]))
        self._hideVectorsAction.setVisible(not all([not item.showVectors for item in items]))

        self._showStreamsAction.setVisible(not all([item.showStreamlines for item in items]))
        self._hideStreamsAction.setVisible(not all([not item.showStreamlines for item in items]))

        self._moreAction.setVisible(len(items)==1)  # This, detailed setting, is configured one by one because this may have complex settings.

        self._menu.exec(pos)

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

    @qasync.asyncSlot()
    async def _showActors(self):
        for item in self._selectedItems:
            await item.setActorVisible(True)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _hideActors(self):
        for item in self._selectedItems:
            await item.setActorVisible(False)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _displayWireframe(self):
        for item in self._selectedItems:
            await item.setDisplayMode(DisplayMode.WIREFRAME)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _displaySurface(self):
        for item in self._selectedItems:
            await item.setDisplayMode(DisplayMode.SURFACE)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _displayWireSurfaceWithEdges(self):
        for item in self._selectedItems:
            await item.setDisplayMode(DisplayMode.SURFACE_EDGE)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _opacityChanged(self):
        opacity = self._opacityDialog.opacity()
        for item in self._selectedItems:
            await item.setOpacity(opacity)

    @qasync.asyncSlot()
    async def _colorChanged(self):
        color = self._colorDialog.selectedColor()
        for item in self._selectedItems:
            await item.setActorColor(color)

    @qasync.asyncSlot()
    async def _solidColorMode(self):
        self._colorAction.setEnabled(True)
        for item in self._selectedItems:
            await item.setColorMode(ColorMode.SOLID)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _fieldColorMode(self):
        self._colorAction.setEnabled(False)
        for item in self._selectedItems:
            await item.setColorMode(ColorMode.FIELD)

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
    async def _showVectors(self):
        for item in self._selectedItems:
                await item.showVectors()

        self._view.refresh()

    @qasync.asyncSlot()
    async def _hideVectors(self):
        for item in self._selectedItems:
            await item.hideVectors()

        self._view.refresh()

    @qasync.asyncSlot()
    async def _showStreams(self):
        for item in self._selectedItems:
            await item.showStreamlines()

        self._view.refresh()

    @qasync.asyncSlot()
    async def _hideStreams(self):
        for item in self._selectedItems:
            await item.hideStreamlines()

        self._view.refresh()

    def _addItem(self, rs: ReportingScaffold) -> UUID:
        did = uuid4()
        contour: Contour = self._report

        item = DisplayItem(self._scaffoldTreeWidget, did, contour, rs, contour.internalMesh, contour.field, contour.useNodeValues, self._lookupTable, self._view)

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

    async def _reportingScaffoldAdded(self, uuid: UUID):
        rs = self._report.reportingScaffolds[uuid]
        displayUuid = self._addItem(rs)

        self._scaffold2displayItem[uuid] = displayUuid

        self._view.refresh()

    async def _reportingScaffoldRemoving(self, uuid: UUID):
        displayUuid = self._scaffold2displayItem[uuid]
        self.removeItem(displayUuid)

        del self._scaffold2displayItem[uuid]

        self._view.refresh()

    def _setUpContextMenu(self, menu: QMenu):
        self._opacityDialog = OpacityDialog(self)
        self._colorDialog = QColorDialog(self)
        self._reportingScaffoldDialog = ReportingScaffoldDialog(self)

        self._showAction: QAction = menu.addAction(self.tr('Show'), self._showActors)

        self._hideAction: QAction = menu.addAction(self.tr('Hide'), self._hideActors)

        self._opacityAction: QAction = menu.addAction(self.tr('Opacity'), self._openOpacityDialog)

        self._colorAction: QAction = menu.addAction(self.tr('Color'), self._openColorDialog)

        self._colorModeMenu: QMenu = menu.addMenu(self.tr('Color Mode'))

        self._solidColorAction: QAction = self._colorModeMenu.addAction(self.tr('Solid'), self._solidColorMode)
        self._solidColorAction.setCheckable(True)

        self._fieldColorAction: QAction = self._colorModeMenu.addAction(self.tr('Field'), self._fieldColorMode)
        self._fieldColorAction.setCheckable(True)

        self._displayModeMenu: QMenu = menu.addMenu(self.tr('Display Mode'))

        self._wireFrameDisplayAction: QAction = self._displayModeMenu.addAction(self.tr('Wireframe'), self._displayWireframe)
        self._wireFrameDisplayAction.setCheckable(True)

        self._surfaceDisplayAction: QAction = self._displayModeMenu.addAction(self.tr('Surface'), self._displaySurface)
        self._surfaceDisplayAction.setCheckable(True)

        self._surfaceEdgeDisplayAction: QAction = self._displayModeMenu.addAction(self.tr('Surface with Edges'), self._displayWireSurfaceWithEdges)
        self._surfaceEdgeDisplayAction.setCheckable(True)

        menu.addSeparator()

        self._showVectorsAction: QAction = menu.addAction(self.tr('Show Vectors'), self._showVectors)
        self._hideVectorsAction: QAction = menu.addAction(self.tr('Hide Vectors'), self._hideVectors)

        menu.addSeparator()

        self._showStreamsAction: QAction = menu.addAction(self.tr('Show Streamlines'), self._showStreams)
        self._hideStreamsAction: QAction = menu.addAction(self.tr('Hide Streamlines'), self._hideStreams)

        menu.addSeparator()

        self._moreAction: QAction = menu.addAction(self.tr('More...'), self._openReportingScaffoldDialog)

    def _openOpacityDialog(self):
        if all([item.opacity == self._selectedItems[0].opacity for item in self._selectedItems]):
            opacity = self._selectedItems[0].opacity
        else:
            opacity = 0.9

        self._opacityDialog.setOpacity(opacity)
        self._opacityDialog.open()

    def _openColorDialog(self):
        if all([item.color == self._selectedItems[0].color for item in self._selectedItems]):
            color = self._selectedItems[0].color
        else:
            color = Qt.GlobalColor.white

        self._colorDialog.setCurrentColor(color)
        self._colorDialog.open()

    def _openReportingScaffoldDialog(self):
        self._reportingScaffoldDialog.open(self._selectedItems[0])  # this is for one item only

