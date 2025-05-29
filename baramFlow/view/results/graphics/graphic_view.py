#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import UUID, uuid4

from PySide6.QtGui import QAction

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QColorDialog, QHeaderView, QMenu, QWidget

import qasync

from vtkmodules.vtkCommonCore import vtkLookupTable, vtkScalarsToColors
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.app import app

from baramFlow.base.graphic.color_scheme import getColorTable
from baramFlow.base.graphic.graphic import Graphic
from baramFlow.base.field import FieldType, VectorComponent
from baramFlow.base.graphic.display_item import DisplayItem
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB

from baramFlow.view.results.graphics.colormap_dialog import ColormapDialog
from baramFlow.view.results.graphics.display_control_panel_ui import Ui_DisplayControlPanel
from baramFlow.view.results.graphics.opacity_dialog import OpacityDialog
from baramFlow.view.results.graphics.display_item_dialog import DisplayItemDialog
from baramFlow.view.results.graphics.scalar_bar_widget import ScalarBarWidget
from baramFlow.view.widgets.rendering_view import RenderingView

from widgets.overlay_frame import OverlayFrame

from baramFlow.view.results.graphics.display_control import ColorMode, DisplayMode, DisplayControl, Column
from widgets.progress_dialog import ProgressDialog


VTK_ORIENT_HORIZONTAL = 0
VTK_ORIENT_VERTICAL   = 1


class VisualReportView(RenderingView):
    def __init__(self, parent: QWidget, graphic: Graphic):
        super().__init__(parent)

        # To Remove RenderingMode tool menu, which is not used in Visual Report
        layout = self._ui.renderingMode.parentWidget().layout()
        layout.removeWidget(self._ui.renderingMode)

        # Remove the combobox for "Rendering Mode"
        self._ui.renderingMode.setParent(None)  # type: ignore
        self._ui.renderingMode = None           # type: ignore

        self._dialog = None

        self._lookupTable = vtkLookupTable()
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._overlayFrame = OverlayFrame(self._view)

        self._displayControlUi = Ui_DisplayControlPanel()
        self._displayControlUi.setupUi(self._overlayFrame)

        self._treeWidget = self._displayControlUi.treeWidget
        self._treeWidget.headerItem().setText(Column.NAME_COLUMN, self.tr('Name'))
        self._treeWidget.headerItem().setText(Column.TYPE_COLUMN, self.tr('Type'))
        self._treeWidget.headerItem().setText(Column.COLOR_COLUMN, '')

        self._menu = QMenu(self._treeWidget)
        self._setUpContextMenu(self._menu)

        self._controls: dict[UUID, DisplayControl] = {}
        self._selectedControls: list[DisplayControl] = []

        self._treeWidget.setColumnWidth(Column.COLOR_COLUMN, 20)

        self._treeWidget.header().setSectionResizeMode(Column.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        self._treeWidget.header().setSectionResizeMode(Column.TYPE_COLUMN, QHeaderView.ResizeMode.ResizeToContents)

        self._colormap = ScalarBarWidget(self, graphic, self._colormapDoubleClicked)
        self._colormap.SetInteractor(self._view.interactor())

        actor: vtkScalarBarActor = self._colormap.GetScalarBarActor()
        actor.SetLookupTable(self._lookupTable)
        actor.UnconstrainedFontSizeOn()

        actor.GetTitleTextProperty().SetLineSpacing(1.5)
        actor.SetTitle(graphic.fieldDisplayName+'\n')  # '\n' is added to set title apart from the bar

        representation = self._colormap.GetScalarBarRepresentation()
        representation.SetOrientation(VTK_ORIENT_HORIZONTAL)
        representation.SetPosition(0.35, 0.03)
        representation.SetPosition2(0.3, 0.1)  # Relative position from position1

        self._colormap.On()

        self._graphic = graphic

        self._scaffold2displayControl: dict[UUID, UUID] = {}
        self._updatedScaffolds: set[UUID] = set()

        graphic.rangeMin, graphic.rangeMax = graphic.getValueRange(graphic.useNodeValues, graphic.relevantScaffoldsOnly)

        for scaffoldUuid in self._graphic.getScaffolds():
            item = self._graphic.getDisplayItem(scaffoldUuid)
            displayUuid = self._createDisplayControl(item)

            self._scaffold2displayControl[item.scaffoldUuid] = displayUuid

        self._view.fitCamera()

        self._updateLookupTable()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._treeWidget.customContextMenuRequested.connect(self._showContextMenu)
        self._treeWidget.itemSelectionChanged.connect(self._selectedItemsChanged)
        self._view.customContextMenuRequested.connect(self._showContextMenuOnRenderingView)
        self._view.actorPicked.connect(self._actorPicked)

        self._opacityDialog.accepted.connect(self._opacityChanged)
        self._colorDialog.accepted.connect(self._colorChanged)

        ScaffoldsDB().scaffoldUpdated.asyncConnect(self._scaffoldUpdated)

        self._graphic.instanceUpdated.asyncConnect(self._reportUpdated)
        self._graphic.displayItemAdded.asyncConnect(self._displayItemAdded)
        self._graphic.displayItemRemoving.asyncConnect(self._displayItemRemoving)

    def _disconnectSignalsSlots(self):
        ScaffoldsDB().scaffoldUpdated.disconnect(self._scaffoldUpdated)

        self._graphic.instanceUpdated.disconnect(self._reportUpdated)
        self._graphic.displayItemAdded.disconnect(self._displayItemAdded)
        self._graphic.displayItemRemoving.disconnect(self._displayItemRemoving)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlayFrame.updateGeometry()

    def closeEvent(self, event):
        self._disconnectSignalsSlots()

        super().closeEvent(event)

    def _colormapDoubleClicked(self):
        self._dialog = ColormapDialog(self, self._graphic)
        self._dialog.accepted.connect(self._updateLookupTable)
        self._dialog.open()

    def _updateLookupTable(self):
        graphic: Graphic = self._graphic
        levels = graphic.numberOfLevels

        actor: vtkScalarBarActor = self._colormap.GetScalarBarActor()
        actor.SetTitle(graphic.fieldDisplayName+'\n')  # '\n' is added to set title apart from the bar
        actor.SetMaximumNumberOfColors(levels)

        if graphic.field.type == FieldType.VECTOR:
            if graphic.fieldComponent == VectorComponent.MAGNITUDE:
                if self._lookupTable.GetVectorMode() != vtkScalarsToColors.MAGNITUDE:
                    self._lookupTable.SetVectorMode(vtkScalarsToColors.MAGNITUDE)
            else:
                if self._lookupTable.GetVectorMode() != vtkScalarsToColors.COMPONENT:
                    self._lookupTable.SetVectorMode(vtkScalarsToColors.COMPONENT)

                if graphic.fieldComponent == VectorComponent.X:
                    if self._lookupTable.GetVectorComponent() != 0:
                        self._lookupTable.SetVectorComponent(0)
                elif graphic.fieldComponent == VectorComponent.Y:
                    if self._lookupTable.GetVectorComponent() != 1:
                        self._lookupTable.SetVectorComponent(1)
                elif graphic.fieldComponent == VectorComponent.Z:
                    if self._lookupTable.GetVectorComponent() != 2:
                        self._lookupTable.SetVectorComponent(2)

        self._lookupTable.SetNumberOfTableValues(levels)

        if graphic.useCustomColorScheme:
            rMin, gMin, bMin, _ = graphic.customMinColor.getRgbF()
            rMax, gMax, bMax, _ = graphic.customMaxColor.getRgbF()

            if levels > 1:
                rInc = (rMax - rMin) / (levels-1)
                gInc = (gMax - gMin) / (levels-1)
                bInc = (bMax - bMin) / (levels-1)
                for i in range(0, levels):
                    r = rMin + i * rInc
                    g = gMin + i * gInc
                    b = bMin + i * bInc
                    self._lookupTable.SetTableValue(i, r, g, b)
            else:
                self._lookupTable.SetTableValue(0, rMin, gMin, bMin)

        else:
            table = getColorTable(graphic.colorScheme, levels)
            for i in range(0, levels):
                self._lookupTable.SetTableValue(i, table[i*3], table[i*3+1], table[i*3+2])

        self._lookupTable.SetAboveRangeColor(0, 0, 0, 0)  # Transparent
        self._lookupTable.SetBelowRangeColor(0, 0, 0, 0)  # Transparent

        # White for NaN Value, for missing fields in Solid Region for example
        # Transparent value of 0.5 might be better
        # But it did not work well on OpenGL
        self._lookupTable.SetNanColor(1, 1, 1, 1)

        if graphic.useCustomRange:
            self._lookupTable.SetTableRange(float(graphic.customRangeMin), float(graphic.customRangeMax))
        else:
            self._lookupTable.SetTableRange(graphic.rangeMin, graphic.rangeMax)

        if graphic.clipToRange:
            self._lookupTable.UseAboveRangeColorOn()
            self._lookupTable.UseBelowRangeColorOn()
        else:
            self._lookupTable.UseAboveRangeColorOff()
            self._lookupTable.UseBelowRangeColorOff()

        self._lookupTable.Build()

    async def _scaffoldUpdated(self, uuid: UUID):
        if uuid not in self._scaffold2displayControl:
            return  # Not my scaffold

        scaffold = ScaffoldsDB().getScaffold(uuid)
        dataSet = await scaffold.getDataSet(self._graphic.polyMesh)

        displayUuid = self._scaffold2displayControl[uuid]
        control = self._controls[displayUuid]

        control.displayItem.dataSet = dataSet

        await control.updateScaffoldInfo()

        self._view.refresh()

    async def _reportUpdated(self, uuid: UUID):

        for did in self._controls:
            control = self._controls[did]
            await control.updateScaffoldInfo()

        self._updateLookupTable()

        self._view.refresh()

    def _selectedItemsChanged(self):
        ids = []
        for control in self._controls.values():
            control.setHighlighted(control.isSelected())
            if control.isSelected():
                ids.append(control.did())

        self._view.refresh()

    def _executeContextMenu(self, pos):
        controls: list[DisplayControl] = self._treeWidget.selectedItems()
        if len(controls) == 0:
            return

        self._selectedControls = controls

        self._showAction.setVisible(not all([control.visibility for control in controls]))
        self._hideAction.setVisible(not all([not control.visibility for control in controls]))

        self._colorAction.setEnabled(not all([control.colorMode == ColorMode.FIELD for control in controls]))

        self._solidColorAction.setChecked(all([control.colorMode == ColorMode.SOLID for control in controls]))
        self._fieldColorAction.setChecked(all([control.colorMode == ColorMode.FIELD for control in controls]))

        self._wireFrameDisplayAction.setChecked(all([control.displayMode == DisplayMode.WIREFRAME for control in controls]))
        self._surfaceDisplayAction.setChecked(all([control.displayMode == DisplayMode.SURFACE for control in controls]))
        self._surfaceEdgeDisplayAction.setChecked(all([control.displayMode == DisplayMode.SURFACE_EDGE for control in controls]))

        self._cullFrontFaceAction.setVisible(not all([control.frontFaceCulling for control in controls]))
        self._revealFrontFaceAction.setVisible(not all([not control.frontFaceCulling for control in controls]))

        self._showVectorsAction.setVisible(not all([control.vectorsOn for control in controls]))
        self._hideVectorsAction.setVisible(not all([not control.vectorsOn for control in controls]))

        self._showStreamsAction.setVisible(not all([control.streamlinesOn for control in controls]))
        self._hideStreamsAction.setVisible(not all([not control.streamlinesOn for control in controls]))

        self._moreAction.setVisible(len(controls)==1)  # This, detailed setting, is configured one by one because this may have complex settings.

        self._menu.exec(pos)

    def _showContextMenu(self, pos):
        self._executeContextMenu(self._treeWidget.mapToGlobal(pos))

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
        for control in self._selectedControls:
            await control.setActorVisible(True)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _hideActors(self):
        for control in self._selectedControls:
            await control.setActorVisible(False)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _displayWireframe(self):
        for control in self._selectedControls:
            await control.setDisplayMode(DisplayMode.WIREFRAME)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _displaySurface(self):
        for control in self._selectedControls:
            await control.setDisplayMode(DisplayMode.SURFACE)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _displayWireSurfaceWithEdges(self):
        for control in self._selectedControls:
            await control.setDisplayMode(DisplayMode.SURFACE_EDGE)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _cullFrontFace(self):
        for control in self._selectedControls:
            await control.cullFrontFace()

        self._view.refresh()

    @qasync.asyncSlot()
    async def _revealFrontFace(self):
        for control in self._selectedControls:
            await control.revealFrontFace()

        self._view.refresh()

    @qasync.asyncSlot()
    async def _opacityChanged(self):
        opacity = self._opacityDialog.opacity()
        for control in self._selectedControls:
            await control.setOpacity(opacity)

    @qasync.asyncSlot()
    async def _colorChanged(self):
        color = self._colorDialog.selectedColor()
        for control in self._selectedControls:
            await control.setActorColor(color)

    @qasync.asyncSlot()
    async def _solidColorMode(self):
        self._colorAction.setEnabled(True)
        for control in self._selectedControls:
            await control.setColorMode(ColorMode.SOLID)

        self._view.refresh()

    @qasync.asyncSlot()
    async def _fieldColorMode(self):
        self._colorAction.setEnabled(False)
        for control in self._selectedControls:
            await control.setColorMode(ColorMode.FIELD)

        self._view.refresh()

    def _actorPicked(self, actor: vtkActor, ctrlKeyPressed=False, forContextMenu=False):
        if not ctrlKeyPressed and not forContextMenu:
            self._treeWidget.clearSelection()

        if actor:
            print(f'{actor.GetObjectName()} picked')
            control = self._controls[UUID(actor.GetObjectName())]
            if not control.isSelected() and forContextMenu:
                self._treeWidget.clearSelection()

            if ctrlKeyPressed:
                control.setSelected(not control.isSelected())
            else:
                control.setSelected(True)

    def _actorSourceUpdated(self, id_):
        pass

    @qasync.asyncSlot()
    async def _showVectors(self):
        progressDialog = ProgressDialog(self, self.tr('Vectors'), openDelay=500)
        progressDialog.setLabelText(self.tr('Setting up Vectors...'))
        progressDialog.open()

        for control in self._selectedControls:
                await control.showVectors()

        self._view.refresh()
        progressDialog.close()

    @qasync.asyncSlot()
    async def _hideVectors(self):
        for control in self._selectedControls:
            await control.hideVectors()

        self._view.refresh()

    @qasync.asyncSlot()
    async def _showStreams(self):
        progressDialog = ProgressDialog(self, self.tr('Streamlines'), openDelay=500)
        progressDialog.setLabelText(self.tr('Setting up Streamlines...'))
        progressDialog.open()

        for control in self._selectedControls:
            await control.showStreamlines()

        self._view.refresh()

        progressDialog.close()

    @qasync.asyncSlot()
    async def _hideStreams(self):
        for control in self._selectedControls:
            await control.hideStreamlines()

        self._view.refresh()

    def _createDisplayControl(self, displayItem: DisplayItem) -> UUID:
        did = uuid4()
        graphic: Graphic = self._graphic

        control = DisplayControl(self._treeWidget, did, graphic, displayItem, graphic.internalMesh, graphic.field, graphic.useNodeValues, self._lookupTable, self._view)

        self._controls[did] = control

        control.setupColorWidget(self._treeWidget)

        return did

    def removeDisplayControl(self, did: UUID):
        if did not in self._controls:
            return

        for i in range(self._treeWidget.topLevelItemCount()):
            control: DisplayControl = self._treeWidget.topLevelItem(i)
            if control.did() != did:
                continue

            self._treeWidget.takeTopLevelItem(i)

            control.close()

            del self._controls[did]
            del control

            break

    async def _displayItemAdded(self, scaffoldUuid: UUID):
        item = self._graphic.getDisplayItem(scaffoldUuid)
        controlUuid = self._createDisplayControl(item)

        self._scaffold2displayControl[item.scaffoldUuid] = controlUuid

        self._view.refresh()

    async def _displayItemRemoving(self, scaffoldUuid: UUID):
        item = self._graphic.getDisplayItem(scaffoldUuid)
        controlUuid = self._scaffold2displayControl[item.scaffoldUuid]
        self.removeDisplayControl(controlUuid)

        del self._scaffold2displayControl[item.scaffoldUuid]

        self._view.refresh()

    def _setUpContextMenu(self, menu: QMenu):
        self._opacityDialog = OpacityDialog(self)
        self._colorDialog = QColorDialog(self)
        self._displayItemDialog = DisplayItemDialog(self)

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

        self._cullFrontFaceAction: QAction = menu.addAction(self.tr('Cull Front-face'), self._cullFrontFace)
        self._revealFrontFaceAction: QAction = menu.addAction(self.tr('Reveal Front-face'), self._revealFrontFace)

        menu.addSeparator()

        self._showVectorsAction: QAction = menu.addAction(self.tr('Show Vectors'), self._showVectors)
        self._hideVectorsAction: QAction = menu.addAction(self.tr('Hide Vectors'), self._hideVectors)

        menu.addSeparator()

        self._showStreamsAction: QAction = menu.addAction(self.tr('Show Streamlines'), self._showStreams)
        self._hideStreamsAction: QAction = menu.addAction(self.tr('Hide Streamlines'), self._hideStreams)

        menu.addSeparator()

        self._moreAction: QAction = menu.addAction(self.tr('More...'), self._openDisplayItemDialog)

    def _openOpacityDialog(self):
        if all([control.opacity == self._selectedControls[0].opacity for control in self._selectedControls]):
            opacity = self._selectedControls[0].opacity
        else:
            opacity = 0.9

        self._opacityDialog.setOpacity(opacity)
        self._opacityDialog.open()

    def _openColorDialog(self):
        if all([control.color == self._selectedControls[0].color for control in self._selectedControls]):
            color = self._selectedControls[0].color
        else:
            color = Qt.GlobalColor.white

        self._colorDialog.setCurrentColor(color)
        self._colorDialog.open()

    def _openDisplayItemDialog(self):
        self._displayItemDialog.setDisplayControl(self._selectedControls[0])  # this is for only one item
        self._displayItemDialog.open()

