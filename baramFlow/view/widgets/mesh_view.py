#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QColorDialog, QHeaderView, QMenu, QWidget

from baramFlow.app import app
from baramFlow.base.event_bus import EventBus
from baramFlow.coredb.boundary_db import BoundaryType
from baramFlow.coredb.region_db import RegionDB
from baramFlow.mesh.mesh_model import DisplayMode, MeshModel

from widgets.opacity_dialog import OpacityDialog
from widgets.overlay_frame import OverlayFrame

from .boundary_display_control import BoundaryDisplayControl, Column
from .boundary_display_control_panel_ui import Ui_BoundaryDisplayControlPanel
from .rendering_view import RenderingView


class MeshView(RenderingView):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._overlayFrame = OverlayFrame(self._view)

        self._displayControlUi = Ui_BoundaryDisplayControlPanel()
        self._displayControlUi.setupUi(self._overlayFrame)

        self._treeWidget = self._displayControlUi.treeWidget
        self._treeWidget.headerItem().setText(Column.REGION_COLUMN, self.tr('Region'))
        self._treeWidget.headerItem().setText(Column.NAME_COLUMN, self.tr('Name'))
        self._treeWidget.headerItem().setText(Column.TYPE_COLUMN, self.tr('Type'))
        self._treeWidget.headerItem().setText(Column.COLOR_COLUMN, '')

        self._treeWidget.setColumnWidth(Column.COLOR_COLUMN, 20)

        self._treeWidget.header().setSectionsMovable(False)

        self._treeWidget.header().setSectionResizeMode(Column.REGION_COLUMN, QHeaderView.ResizeMode.Interactive)
        self._treeWidget.header().setSectionResizeMode(Column.NAME_COLUMN, QHeaderView.ResizeMode.Interactive)
        self._treeWidget.header().setSectionResizeMode(Column.TYPE_COLUMN, QHeaderView.ResizeMode.Stretch)
        self._treeWidget.header().setSectionResizeMode(Column.COLOR_COLUMN, QHeaderView.ResizeMode.Fixed)

        self._menu = QMenu(self._treeWidget)
        self._setUpContextMenu(self._menu)

        self._controls: dict[int, BoundaryDisplayControl] = {}
        self._selectedControls: list[BoundaryDisplayControl] = []

        self._connectSignalsSlots()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlayFrame.updateGeometry()

    def rebuildBoundaryDisplayControls(self, meshModel: MeshModel, boundaryInfos):
        for control in self._controls.values():
            control.close()

        self._treeWidget.clear()
        self._controls = {}
        self._selectedControls = []

        self._treeWidget.setColumnHidden(Column.REGION_COLUMN, not RegionDB.isMultiRegion())

        for bcid, rname, bcname, bctype in boundaryInfos:
            actorInfo = meshModel.actorInfo(bcid)
            control = BoundaryDisplayControl(self._treeWidget, bcid, rname, bcname, bctype, actorInfo, self._view)
            control.setupColorWidget(self._treeWidget)
            self._controls[bcid] = control

        self._view.refresh()

    def _setUpContextMenu(self, menu: QMenu):
        self._opacityDialog = OpacityDialog(self)
        self._colorDialog = QColorDialog(self)

        self._showAction: QAction = menu.addAction(self.tr('Show'), self._showActors)
        self._hideAction: QAction = menu.addAction(self.tr('Hide'), self._hideActors)

        menu.addAction(self.tr('Opacity'), self._openOpacityDialog)
        menu.addAction(self.tr('Color'), self._openColorDialog)

        displayModeMenu: QMenu = menu.addMenu(self.tr('Display Mode'))

        self._wireFrameDisplayAction: QAction = displayModeMenu.addAction(self.tr('Wireframe'), self._displayWireframe)
        self._wireFrameDisplayAction.setCheckable(True)

        self._surfaceDisplayAction: QAction = displayModeMenu.addAction(self.tr('Surface'), self._displaySurface)
        self._surfaceDisplayAction.setCheckable(True)

        self._surfaceEdgeDisplayAction: QAction = displayModeMenu.addAction(self.tr('Surface with Edges'), self._displaySurfaceWithEdges)
        self._surfaceEdgeDisplayAction.setCheckable(True)

        self._featureDisplayAction: QAction = displayModeMenu.addAction(self.tr('Feature'), self._displayFeature)
        self._featureDisplayAction.setCheckable(True)

        self._cullFrontFaceAction: QAction = menu.addAction(self.tr('Cull Front-face'), self._cullFrontFace)
        self._revealFrontFaceAction: QAction = menu.addAction(self.tr('Reveal Front-face'), self._revealFrontFace)

    def _connectSignalsSlots(self):
        self._view.actorPicked.connect(self._actorPicked)
        self._treeWidget.customContextMenuRequested.connect(self._showContextMenu)
        self._treeWidget.itemSelectionChanged.connect(self._selectedItemsChanged)
        self._view.customContextMenuRequested.connect(self._showContextMenuOnRenderingView)

        self._opacityDialog.accepted.connect(self._opacityChanged)
        self._colorDialog.accepted.connect(self._colorChanged)

        EventBus().onBoundaryTypeChange.connect(self._onBoundaryTypeChanged)

    def _onBoundaryTypeChanged(self, bcid: str, oldType: BoundaryType, newType: BoundaryType):
        control = self._controls.get(int(bcid))
        if control is not None:
            control.setType(newType)

    def _selectedItemsChanged(self):
        for control in self._controls.values():
            control.setHighlighted(control.isSelected())

        self._view.refresh()

    def _executeContextMenu(self, pos):
        controls: list[BoundaryDisplayControl] = self._treeWidget.selectedItems()
        if len(controls) == 0:
            return

        self._selectedControls = controls

        self._showAction.setVisible(not all(c.visibility for c in controls))
        self._hideAction.setVisible(not all(not c.visibility for c in controls))

        self._wireFrameDisplayAction.setChecked(all(c.displayMode == DisplayMode.DISPLAY_MODE_WIREFRAME for c in controls))
        self._surfaceDisplayAction.setChecked(all(c.displayMode == DisplayMode.DISPLAY_MODE_SURFACE for c in controls))
        self._surfaceEdgeDisplayAction.setChecked(all(c.displayMode == DisplayMode.DISPLAY_MODE_SURFACE_EDGE for c in controls))
        self._featureDisplayAction.setChecked(all(c.displayMode == DisplayMode.DISPLAY_MODE_FEATURE for c in controls))
        self._featureDisplayAction.setVisible(all(c.hasFeature for c in controls))

        self._cullFrontFaceAction.setVisible(not all(c.frontFaceCulling for c in controls))
        self._revealFrontFaceAction.setVisible(not all(not c.frontFaceCulling for c in controls))

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

    def _actorPicked(self, actor, ctrlKeyPressed=False, forContextMenu=False):
        if not ctrlKeyPressed and not forContextMenu:
            self._treeWidget.clearSelection()

        if actor:
            name = actor.GetObjectName()
            control = self._controls.get(int(name)) if name.isdigit() else None
            if control is None:
                return

            if not control.isSelected() and forContextMenu:
                self._treeWidget.clearSelection()

            if ctrlKeyPressed:
                control.setSelected(not control.isSelected())
            else:
                control.setSelected(True)

    def _showActors(self):
        for control in self._selectedControls:
            control.setActorVisible(True)

        self._view.refresh()

    def _hideActors(self):
        for control in self._selectedControls:
            control.setActorVisible(False)

        self._view.refresh()

    def _displayWireframe(self):
        for control in self._selectedControls:
            control.setDisplayMode(DisplayMode.DISPLAY_MODE_WIREFRAME)

        self._view.refresh()

    def _displaySurface(self):
        for control in self._selectedControls:
            control.setDisplayMode(DisplayMode.DISPLAY_MODE_SURFACE)

        self._view.refresh()

    def _displaySurfaceWithEdges(self):
        for control in self._selectedControls:
            control.setDisplayMode(DisplayMode.DISPLAY_MODE_SURFACE_EDGE)

        self._view.refresh()

    def _displayFeature(self):
        for control in self._selectedControls:
            control.setDisplayMode(DisplayMode.DISPLAY_MODE_FEATURE)

        self._view.refresh()

    def _cullFrontFace(self):
        for control in self._selectedControls:
            control.cullFrontFace()

        self._view.refresh()

    def _revealFrontFace(self):
        for control in self._selectedControls:
            control.revealFrontFace()

        self._view.refresh()

    def _opacityChanged(self):
        opacity = self._opacityDialog.opacity()
        for control in self._selectedControls:
            control.setOpacity(opacity)

        self._view.refresh()

    def _colorChanged(self):
        color = self._colorDialog.selectedColor()
        for control in self._selectedControls:
            control.setActorColor(color)

        self._view.refresh()

    def _openOpacityDialog(self):
        if all(c.opacity == self._selectedControls[0].opacity for c in self._selectedControls):
            opacity = self._selectedControls[0].opacity
        else:
            opacity = 0.9

        self._opacityDialog.setOpacity(opacity)
        self._opacityDialog.open()

    def _openColorDialog(self):
        if all(c.color == self._selectedControls[0].color for c in self._selectedControls):
            color = self._selectedControls[0].color
        else:
            color = Qt.GlobalColor.white

        self._colorDialog.setCurrentColor(color)
        self._colorDialog.open()
