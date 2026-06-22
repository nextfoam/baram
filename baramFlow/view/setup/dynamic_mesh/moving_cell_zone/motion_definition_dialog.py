#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy
from uuid import uuid4

import qasync

from PySide6.QtWidgets import QDialog, QListWidgetItem, QMenu

from baramFlow.base.dynamic_mesh.motion_function import MotionFunction, MotionFunctionType
from baramFlow.base.event_bus import EventBus
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.view.setup.dynamic_mesh.motion_functions.motion_function_widget import MotionFunctionWidget, FUNCTION_TYPE_NAMES
from baramFlow.view.setup.dynamic_mesh.motion_functions.motion_function_dialogs import MOTION_FUNCTION_DIALOGS
from baramFlow.view.widgets.multi_selector_dialog import MultiSelectorDialog
from widgets.async_message_box import AsyncMessageBox

from .motion_definition_dialog_ui import Ui_MotionDefinitionDialog


class MotionDefinitionDialog(QDialog):
    def __init__(self, parent, motionDefinition, existingNames=None):
        super().__init__(parent)

        self._ui = Ui_MotionDefinitionDialog()
        self._ui.setupUi(self)

        self._motionDefinition = motionDefinition
        self._motionFunctions = [deepcopy(mf) for mf in motionDefinition.motionFunctions]
        self._existingNames = existingNames or set()

        self._ui.name.setText(motionDefinition.name)

        self._addMenu = QMenu(self._ui.addButton)
        for ft in [MotionFunctionType.ROTATION, MotionFunctionType.ROTATING_OSCILLATION,
                    MotionFunctionType.LINEAR_TRANSLATION, MotionFunctionType.LINEAR_OSCILLATION,
                    MotionFunctionType.MANUAL_POSITION]:
            action = self._addMenu.addAction(FUNCTION_TYPE_NAMES[ft])
            action.setData(ft)
            action.triggered.connect(lambda checked=False, ftype=ft: self._addMotionFunction(ftype))
        self._ui.addButton.setMenu(self._addMenu)

        self._connectSignalsSlots()

        self._loadMotionFunctions()
        self._setCellZones(motionDefinition.cellZones)

    def _connectSignalsSlots(self):
        self._ui.selectButton.clicked.connect(self._selectCellZones)
        self._ui.mfList.customContextMenuRequested.connect(self._showContextMenu)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self.reject)

    def _loadMotionFunctions(self):
        self._ui.mfList.clear()
        for mf in self._motionFunctions:
            widget = MotionFunctionWidget(mf)
            item = QListWidgetItem()
            item.setSizeHint(widget.size())
            self._ui.mfList.addItem(item)
            self._ui.mfList.setItemWidget(item, widget)

    def _setCellZones(self, cellZones):
        self._motionDefinition.cellZones = cellZones

        self._ui.cellZones.clear()
        for czid in cellZones:
            self._ui.cellZones.addItem(CellZoneDB.getCellZoneText(czid))

    def _addMotionFunction(self, functionType: MotionFunctionType):
        mf = MotionFunction(uuid=uuid4(), order=len(self._motionFunctions) + 1,
                            functionType=functionType)
        self._dialog = MOTION_FUNCTION_DIALOGS[functionType](self, mf)
        self._dialog.accepted.connect(lambda: self._motionFunctionAdded(mf))
        self._dialog.open()

    def _motionFunctionAdded(self, mf):
        self._motionFunctions.append(mf)
        widget = MotionFunctionWidget(mf)
        item = QListWidgetItem()
        item.setSizeHint(widget.size())
        self._ui.mfList.addItem(item)
        self._ui.mfList.setItemWidget(item, widget)

    def _showContextMenu(self, pos):
        row = self._ui.mfList.currentRow()
        if row < 0:
            return

        menu = QMenu(self)
        if row > 0:
            menu.addAction(self.tr('Move Up')).triggered.connect(lambda: self._moveItem(row, row - 1))
        if row < self._ui.mfList.count() - 1:
            menu.addAction(self.tr('Move Down')).triggered.connect(lambda: self._moveItem(row, row + 1))

        menu.addAction(self.tr('Edit')).triggered.connect(self._editCurrentMotionFunction)
        menu.addAction(self.tr('Remove')).triggered.connect(self._removeCurrentMotionFunction)

        menu.exec(self._ui.mfList.mapToGlobal(pos))

    def _moveItem(self, fromRow, toRow):
        self._motionFunctions[fromRow], self._motionFunctions[toRow] = \
            self._motionFunctions[toRow], self._motionFunctions[fromRow]
        self._loadMotionFunctions()
        self._ui.mfList.setCurrentRow(toRow)

    def _editCurrentMotionFunction(self):
        row = self._ui.mfList.currentRow()
        if row < 0:
            return
        mf = self._motionFunctions[row]
        dialogClass = MOTION_FUNCTION_DIALOGS.get(mf.functionType)
        if dialogClass:
            self._dialog = dialogClass(self, mf)
            self._dialog.accepted.connect(lambda: self._motionFunctionEdited(row))
            self._dialog.open()

    def _motionFunctionEdited(self, row):
        widget = self._ui.mfList.itemWidget(self._ui.mfList.item(row))
        if isinstance(widget, MotionFunctionWidget):
            widget.load()

    def _removeCurrentMotionFunction(self):
        row = self._ui.mfList.currentRow()
        if row < 0:
            return
        del self._motionFunctions[row]
        self._ui.mfList.takeItem(row)

    def _selectCellZones(self):
        self._dialog = MultiSelectorDialog(
            self, self.tr('Select Cell Zones'),
            CellZoneDB.getCellZoneOnlySelectorItems(),
            self._motionDefinition.cellZones)
        self._dialog.accepted.connect(self._cellZonesChanged)
        self._dialog.open()

    def _cellZonesChanged(self):
        self._setCellZones(list(self._dialog.selectedItems()))

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            name = self._ui.name.text()
            if name in self._existingNames:
                raise ValueError(self.tr('The name "{0}" is already in use.').format(name))

            if not self._motionFunctions:
                raise ValueError(self.tr('At least one motion function must be defined.'))

        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        for i, mf in enumerate(self._motionFunctions):
            mf.order = i + 1

        self._motionDefinition.name = name
        self._motionDefinition.motionFunctions = self._motionFunctions

        EventBus().onConfigChanged.emit()

        self.accept()
