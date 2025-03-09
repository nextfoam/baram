#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from typing import Optional
from uuid import UUID, uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHeaderView, QHeaderView, QWidget
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.app import app

from baramFlow.coredb.post_field import Field, FieldType, VectorComponent
from widgets.rendering.rendering_widget import RenderingWidget

from .display_context_menu import DisplayContextMenu
from .display_control_ui import Ui_DisplayControl
from .display_item import ColorMode, DisplayMode, Properties, DisplayItem, Column


class DisplayControl(QWidget):
    selectedActorsChanged = Signal(list)
    selectionApplied = Signal()

    def __init__(self, parent, view: RenderingWidget, lookupTable: vtkLookupTable):
        super().__init__(parent)

        self._ui = Ui_DisplayControl()
        self._ui.setupUi(self)

        self._scaffoldList = self._ui.actors
        self._view = view
        self._lookupTable = lookupTable

        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._menu = DisplayContextMenu(self._scaffoldList)

        self._items: dict[UUID, DisplayItem] = {}
        self._selectedItems: list[DisplayItem] = []

        self._scaffoldList.setColumnWidth(Column.COLOR_COLUMN, 20)

        self._scaffoldList.header().setSectionResizeMode(Column.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        self._scaffoldList.header().setSectionResizeMode(Column.TYPE_COLUMN, QHeaderView.ResizeMode.ResizeToContents)


        self._connectSignalsSlots()

    def addItem(self, name, dataSet, field: Field, useNodeValues: bool) -> UUID:
        did = uuid4()
        item = DisplayItem(did, name, dataSet, field, useNodeValues, self._lookupTable)

        self._items[did] = item

        self._scaffoldList.addTopLevelItem(item)
        item.setupColorWidget(self._scaffoldList)

        self._view.addActor(item.actor())

        return did

    def removeItem(self, did: UUID):
        if did not in self._items:
            return

        for i in range(self._scaffoldList.topLevelItemCount()):
            item: DisplayItem = self._scaffoldList.topLevelItem(i)
            if item.did() != did:
                continue

            self._scaffoldList.takeTopLevelItem(i)

            self._view.removeActor(item.actor())

            del self._items[did]
            del item

            break

    def updateItemScaffold
    def updateItem(self, did: UUID, name: str, dataSet) -> UUID:
        if did not in self._items:
            return

        item = self._items[did]
        item.setName(name)
        item.setDataSet(dataSet)
        # for i in range(self._scaffoldList.topLevelItemCount()):
        #     item: DisplayItem = self._scaffoldList.topLevelItem(i)
        #     if item.did() != did:
        #         continue

        #     self._scaffoldList.takeTopLevelItem(i)

        #     self._view.removeActor(item.actor())

        #     item = DisplayItem(did, name, dataSet)
        #     self._items[did] = item

        #     self._scaffoldList.insertTopLevelItem(i, item)
        #     item.setupColorWidget(self._scaffoldList)

        #     self._view.addActor(item.actor())

        #     break

    # def hide(self, actorInfo):
    #     item = self._items[actorInfo.id()]
    #     self._view.removeActor(item.actorInfo().actor())
    #     item.setHidden(True)

    def refreshView(self):
        self._view.refresh()

    def fitView(self):
        self._view.fitCamera()

    def clear(self):
        self._scaffoldList.clear()
        self._view.clear()
        self._items = {}
        self._selectedItems.clear()

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

    # def setSelectedActors(self, ids):
    #     self._scaffoldList.clearSelection()
    #     for i in ids:
    #         if i in self._items:
    #             self._items[i].setSelected(True)

    #     self.selectionApplied.emit()

    def _selectedItemsChanged(self):
        ids = []
        for item in self._items.values():
            item.setHighlighted(item.isSelected())
            if item.isSelected():
                ids.append(item.did())

        self.selectedActorsChanged.emit(ids)
        self._view.refresh()

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
