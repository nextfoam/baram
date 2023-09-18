#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMenu, QColorDialog, QHeaderView

from baramSnappy.app import app
from baramSnappy.db.configurations_schema import Step
from baramSnappy.rendering.actor_info import DisplayMode

from .opacity_dialog import OpacityDialog
from .display_item import DisplayItem, Column
from .cut_tool import CutTool


class ContextMenu(QMenu):
    showActionTriggered = Signal()
    hideActionTriggered = Signal()
    opacitySelected = Signal(float)
    colorPicked = Signal(QColor)
    noCutActionTriggered = Signal(bool)

    wireframeDisplayModeSelected = Signal()
    surfaceDisplayModeSelected = Signal()
    surfaceEdgeDisplayModeSelected = Signal()

    def __init__(self, parent):
        super().__init__(parent)

        self._opacityDialog = OpacityDialog(app.window)
        self._colorDialog = QColorDialog(app.window)
        self._properties = None

        self._showAction = self.addAction(self.tr('Show'), lambda: self.showActionTriggered.emit())
        self._hideAction = self.addAction(self.tr('Hide'), lambda: self.hideActionTriggered.emit())
        self._opacityAction = self.addAction(self.tr('Opacity'), self._openOpacityDialog)
        self._colorAction = self.addAction(self.tr('Color'), self._openColorDialog)

        displayMenu = self.addMenu(self.tr('Display Mode'))
        self._wireFrameDisplayAction = displayMenu.addAction(
            self.tr('Wireframe'), lambda: self.wireframeDisplayModeSelected.emit())
        self._surfaceDisplayAction = displayMenu.addAction(
            self.tr('Surface'), lambda: self.surfaceDisplayModeSelected.emit())
        self._surfaceEdgeDisplayAction = displayMenu.addAction(
            self.tr('Surface with Edges'), lambda: self.surfaceEdgeDisplayModeSelected.emit())

        self._noCutAction = self.addAction(self.tr('No Cut'), self._noCutActionTriggered)

        self._wireFrameDisplayAction.setCheckable(True)
        self._surfaceDisplayAction.setCheckable(True)
        self._surfaceEdgeDisplayAction.setCheckable(True)
        self._noCutAction.setCheckable(True)

        self._connectSignalsSlots()

    def execute(self, pos, properties):
        self._properties = properties

        self._showAction.setVisible(not properties.visibility)
        self._hideAction.setVisible(properties.visibility is None or properties.visibility)
        self._wireFrameDisplayAction.setChecked(properties.displayMode == DisplayMode.WIREFRAME)
        self._surfaceDisplayAction.setChecked(properties.displayMode == DisplayMode.SURFACE)
        self._surfaceEdgeDisplayAction.setChecked(properties.displayMode == DisplayMode.SURFACE_EDGE)
        self._noCutAction.setChecked(properties.cutEnabled is False)

        self.exec(pos)

    def _connectSignalsSlots(self):
        self._opacityDialog.accepted.connect(lambda: self.opacitySelected.emit(self._opacityDialog.opacity()))
        self._colorDialog.accepted.connect(lambda: self.colorPicked.emit(self._colorDialog.selectedColor()))

    def _openOpacityDialog(self):
        self._opacityDialog.setOpacity(self._properties.opacity)
        self._opacityDialog.open()

    def _openColorDialog(self):
        self._colorDialog.setCurrentColor(
            Qt.GlobalColor.white if self._properties.color is None else self._properties.color)
        self._colorDialog.open()

    def _noCutActionTriggered(self):
        self.noCutActionTriggered.emit(not self._properties.cutEnabled)


class DisplayControl(QObject):
    def __init__(self, ui):
        super().__init__()

        self._ui = ui
        self._list = ui.actors
        self._view = ui.renderingView

        self._items = {}
        self._selectedItems = None
        self._dialog = None
        self._menu = ContextMenu(self._list)

        self._cutTool = CutTool(ui)

        self._list.setColumnWidth(Column.COLOR_COLUMN, 20)
        # self._list.setColumnWidth(Column.CUT_ICON_COLUMN, 20)
        # self._list.setColumnWidth(Column.VISIBLE_ICON_COLUMN, 20)

        self._list.header().setSectionResizeMode(Column.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        self._list.header().setSectionResizeMode(Column.TYPE_COLUMN, QHeaderView.ResizeMode.ResizeToContents)

        self._connectSignalsSlots()

    def add(self, actorInfo):
        if actorInfo.id() in self._items:
            item = self._items[actorInfo.id()]
            item.actorInfo().setDataSet(actorInfo.dataSet())
            item.setHidden(False)

            actorInfo = item.actorInfo()
        else:
            actorInfo.sourceChanged.connect(self._actorSourceUpdated)

            item = DisplayItem(actorInfo)
            self._items[actorInfo.id()] = item
            self._list.addTopLevelItem(item)
            item.setupColorWidget(self._list)

        self._view.addActor(actorInfo.actor())

        return actorInfo

    def remove(self, actorInfo):
        index = -1
        for i in range(self._list.topLevelItemCount()):
            if self._list.topLevelItem(i).actorInfo().id() == actorInfo.id():
                index = i
                break

        if index > -1:
            item = self._list.takeTopLevelItem(index)
            self._view.removeActor(item.actorInfo().actor())
            del self._items[str(actorInfo.id())]
            del item
    def hide(self, actorInfo):
        item = self._items[actorInfo.id()]
        self._view.removeActor(item.actorInfo().actor())
        item.setHidden(True)

    def refreshView(self):
        self._view.refresh()

    def fitView(self):
        self._view.fitCamera()

    def openedStepChanged(self, step, prev):
        newCutStatus = step == Step.GEOMETRY.value or step == Step.REGION.value
        prevCutStatus = prev is None or prev == Step.GEOMETRY.value or prev == Step.REGION.value

        if newCutStatus == prevCutStatus:
            return

        if newCutStatus:
            self._cutTool.hide()
        else:
            self._cutTool.show()

    def _connectSignalsSlots(self):
        self._list.customContextMenuRequested.connect(self._showContextMenu)
        self._list.itemSelectionChanged.connect(self._selectedItemsChanged)
        self._view.customContextMenuRequested.connect(self._showContextMenuOnRenderingView)
        self._view.actorPicked.connect(self._actorPicked)
        self._menu.showActionTriggered.connect(self._showActors)
        self._menu.hideActionTriggered.connect(self._hideActors)
        self._menu.opacitySelected.connect(self._applyOpacity)
        self._menu.colorPicked.connect(self._applyColor)
        self._menu.wireframeDisplayModeSelected.connect(self._displayWireframe)
        self._menu.surfaceDisplayModeSelected.connect(self._displaySurface)
        self._menu.surfaceEdgeDisplayModeSelected.connect(self._displayWireSurfaceWithEdges)
        self._menu.noCutActionTriggered.connect(self._applyCutOption)

    def _executeContextMenu(self, pos):
        properties = self._selectedItemsInfo()
        if properties is None:
            return

        self._menu.execute(pos, properties)

    def _showContextMenu(self, pos):
        self._executeContextMenu(self._list.mapToGlobal(pos))

    def _showContextMenuOnRenderingView(self, pos):
        actor = self._view.pickActor(pos.x(), self._view.height() - pos.y() - 1)
        if actor:
            self._actorPicked(actor, False, True)
            self._executeContextMenu(self._view.mapToGlobal(pos))

    def _selectedItemsInfo(self):
        items = self._list.selectedItems()
        if not items:
            return None

        self._selectedItems = []
        properties = items[0].actorInfo().properties()

        for item in items:
            self._selectedItems.append(item)
            properties.merge(item.actorInfo().properties())

        return properties

    def _showActors(self):
        for item in self._selectedItems:
            item.setActorVisible(True)

        self._view.refresh()

    def _hideActors(self):
        for item in self._selectedItems:
            item.setActorVisible(False)

        self._view.refresh()

    def _applyCutOption(self, enabled):
        for item in self._selectedItems:
            item.setCutEnabled(enabled)
            item.actorInfo().cut(self._cutTool.cutters())

        self._view.refresh()

    def _displayWireframe(self):
        for item in self._selectedItems:
            item.actorInfo().setDisplayMode(DisplayMode.WIREFRAME)

        self._view.refresh()

    def _displaySurface(self):
        for item in self._selectedItems:
            item.actorInfo().setDisplayMode(DisplayMode.SURFACE)

        self._view.refresh()

    def _displayWireSurfaceWithEdges(self):
        for item in self._selectedItems:
            item.actorInfo().setDisplayMode(DisplayMode.SURFACE_EDGE)

        self._view.refresh()

    def _applyOpacity(self, opacity):
        for item in self._selectedItems:
            item.actorInfo().setOpacity(opacity)

    def _applyColor(self, color):
        for item in self._selectedItems:
            item.setActorColor(color)

    def _actorPicked(self, actor, ctrlKeyPressed=False, forContextMenu=False):
        if not ctrlKeyPressed and not forContextMenu:
            self._list.clearSelection()

        if actor:
            item = self._items[actor.GetObjectName()]
            if not item.isSelected() and forContextMenu:
                self._list.clearSelection()

            if ctrlKeyPressed:
                item.setSelected(not item.isSelected())
            else:
                item.setSelected(True)

    def _selectedItemsChanged(self):
        for item in self._items.values():
            item.actorInfo().setHighlighted(item.isSelected())

        self._view.refresh()

    def _actorSourceUpdated(self, id_):
        self._items[id_].actorInfo().cut(self._cutTool.cutters())

