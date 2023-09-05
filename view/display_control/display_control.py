#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

from PySide6.QtCore import QObject, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QTreeWidgetItem, QMenu, QLabel, QFrame,  QWidget, QHBoxLayout, QColorDialog, QHeaderView

from app import app
from rendering.actor_info import DisplayMode, ActorType
from .opacity_dialog import OpacityDialog


class Column(IntEnum):
    NAME_COLUMN = 0
    TYPE_COLUMN = auto()
    COLOR_COLUMN = auto()
    # CUT_ICON_COLUMN = auto()
    VISIBLE_ICON_COLUMN = auto()


class ActorItem(QTreeWidgetItem):
    _emptyIcon = QIcon()
    _notCutIcon = QIcon(':graphicsIcons/no-cutter.svg')
    _bulbOnIcon = QIcon(':graphicsIcons/bulb-on.svg')
    _bulbOffIcon = QIcon(':graphicsIcons/bulb-off.svg')

    _types = {
        ActorType.GEOMETRY: QCoreApplication.translate('DisplayControl', 'Geometry'),
        ActorType.BOUNDARY: QCoreApplication.translate('DisplayControl', 'Boundary')
    }

    def __init__(self, actorInfo):
        super().__init__()
        self._actorInfo = None
        self._colorWidget = QLabel()

        self._actorInfo = actorInfo
        self.setText(Column.NAME_COLUMN, actorInfo.name())
        self.setText(Column.TYPE_COLUMN, self._types[actorInfo.type()])
        self._updateColorColumn()
        # self._updateCutIcon()
        self._updateVisibleIcon()

    def setupColorWidget(self, parent):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(9, 1, 9, 1)
        layout.addWidget(self._colorWidget)
        self._colorWidget.setFrameShape(QFrame.Shape.Box)
        self._colorWidget.setMinimumSize(16, 16)
        parent.setItemWidget(self, Column.COLOR_COLUMN, widget)

    def setActorInfo(self, actorInfo):
        actorInfo.setProperties(self._actorInfo.properties())
        self._actorInfo = actorInfo

    def setActorVisible(self, visible):
        self._actorInfo.setVisible(visible)
        self._updateVisibleIcon()

    def setActorColor(self, color):
        self._actorInfo.setColor(color)
        self._updateColorColumn()

    def actorInfo(self):
        return self._actorInfo

    def colorWidget(self):
        return self._colorWidget

    def _updateColorColumn(self):
        color = self._actorInfo.color()
        self._colorWidget.setStyleSheet(f'background-color: rgb({color.red()}, {color.green()}, {color.blue()})')
    #
    # def _updateCutIcon(self):
    #     if not self._actorInfo.isCutEnabled():
    #         self.setIcon(Column.CUT_ICON_COLUMN, self._emptyIcon)
    #     else:
    #         self.setIcon(Column.CUT_ICON_COLUMN, self._notCutIcon)

    def _updateVisibleIcon(self):
        if self._actorInfo.isVisible():
            self.setIcon(Column.VISIBLE_ICON_COLUMN, self._bulbOnIcon)
        else:
            self.setIcon(Column.VISIBLE_ICON_COLUMN, self._bulbOffIcon)


class DisplayControl(QObject):
    def __init__(self, ui):
        super().__init__()

        self._list = ui.actors
        self._view = ui.renderingView

        self._items = {}
        self._selectedItems = None
        self._dialog = None

        self._list.setColumnWidth(Column.COLOR_COLUMN, 20)
        # self._list.setColumnWidth(Column.CUT_ICON_COLUMN, 20)
        self._list.setColumnWidth(Column.VISIBLE_ICON_COLUMN, 20)

        self._list.header().setSectionResizeMode(Column.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        self._list.header().setSectionResizeMode(Column.TYPE_COLUMN, QHeaderView.ResizeMode.ResizeToContents)

        self._connectSignalsSlots()

    def add(self, actorInfo):
        if actorInfo.id() in self._items:
            item = self._items[actorInfo.id()]
            item.setActorInfo(actorInfo)
            item.setHidden(False)
        else:
            item = ActorItem(actorInfo)
            self._items[actorInfo.id()] = item
            self._list.addTopLevelItem(item)
            item.setupColorWidget(self._list)

        self._view.addActor(actorInfo.actor())

    def update(self, actorInfo):
        item = self._items[actorInfo.id()]
        self._view.removeActor(item.actorInfo().actor())
        self._view.addActor(actorInfo.actor())
        item.setActorInfo(actorInfo)

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

    def _connectSignalsSlots(self):
        self._list.customContextMenuRequested.connect(self._showContextMenu)
        self._list.itemSelectionChanged.connect(self._selectedItemsChanged)
        self._view.actorPicked.connect(self._actorPicked)
        self._view.customContextMenuRequested.connect(self._showContextMenuOnRenderingView)

    def _executeContextMenu(self, pos):
        def addAction(menu, text, slot, checked=None):
            action = menu.addAction(text)
            action.triggered.connect(slot)
            if checked is not None:
                action.setCheckable(True)
                action.setChecked(checked)

        properties = self._selectedItemsInfo()
        if properties is None:
            return

        contextMenu = QMenu(self._list)
        if not properties.visibility:
            addAction(contextMenu, self.tr('Show'), self._showActors)
        if properties.visibility is None or properties.visibility:
            addAction(contextMenu, self.tr('Hide'), self._hideActors)
        addAction(contextMenu, self.tr('Opacity'), lambda: self._opacity(properties.opacity))
        addAction(contextMenu, self.tr('Color'), lambda: self._openColorDialog(properties.color))
        displayMenu = contextMenu.addMenu(self.tr('Display Mode'))
        addAction(displayMenu, self.tr('Wireframe'), self._displayWireframe,
                  properties.displayMode == DisplayMode.WIREFRAME)
        addAction(displayMenu, self.tr('Surface'), self._displaySurface,
                  properties.displayMode == DisplayMode.SURFACE)
        addAction(displayMenu, self.tr('Surface with Edges'), self._displayWireSurfaceWithEdges,
                  properties.displayMode == DisplayMode.SURFACE_EDGE)

        contextMenu.exec(pos)

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

    def _opacity(self, opacity):
        self._dialog = OpacityDialog(app.window, opacity)
        self._dialog.accepted.connect(self._applyOpacity)
        self._dialog.open()

    def _openColorDialog(self, color):
        self._dialog = QColorDialog(app.window)
        if color is not None:
            self._dialog.setCurrentColor(color)
        self._dialog.accepted.connect(self._applyColor)
        self._dialog.open()

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

    def _applyOpacity(self):
        opacity = self._dialog.opacity()
        for item in self._selectedItems:
            item.actorInfo().setOpacity(opacity)

    def _applyColor(self):
        color = self._dialog.selectedColor()
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
