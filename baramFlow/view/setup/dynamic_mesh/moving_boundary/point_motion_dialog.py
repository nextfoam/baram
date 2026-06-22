#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy
from uuid import uuid4

import qasync

from PySide6.QtWidgets import QDialog, QButtonGroup, QMenu, QListWidgetItem

from baramFlow.base.dynamic_mesh.motion_function import MotionFunction, MotionFunctionType
from baramFlow.base.dynamic_mesh.moving_boundary import (
    MovingBoundaryEntry, PointMotionType
)
from baramFlow.base.event_bus import EventBus
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, WallMotion, MovingWallMotion
from baramFlow.view.setup.dynamic_mesh.motion_functions.motion_function_widget import MotionFunctionWidget, FUNCTION_TYPE_NAMES
from baramFlow.view.setup.dynamic_mesh.motion_functions.motion_function_dialogs import MOTION_FUNCTION_DIALOGS
from widgets.async_message_box import AsyncMessageBox

from .point_motion_type_dialog_ui import Ui_PointMotionTypeDialog
from .point_motion_dialog_ui import Ui_PointMotionDialog


POINT_MOTION_TYPE_NAMES = {
    PointMotionType.FIXED: 'Fixed',
    PointMotionType.SLIP: 'Slip',
    PointMotionType.PRESCRIBED_MOTION: 'Prescribed Motion',
    PointMotionType.RIGID_BODY_MOTION: 'Rigid Body Motion',
    PointMotionType.CYCLIC: 'Cyclic',
    PointMotionType.SYMMETRY: 'Symmetry',
    PointMotionType.EMPTY: 'Empty',
    PointMotionType.WEDGE: 'Wedge',
}


class PointMotionTypeDialog(QDialog):
    """Small dialog for selecting point motion type."""
    def __init__(self, parent, currentType: PointMotionType, allowedTypes: set[PointMotionType]):
        super().__init__(parent)

        self._ui = Ui_PointMotionTypeDialog()
        self._ui.setupUi(self)

        self._buttonGroup = QButtonGroup(self)
        self._radioMap = {
            PointMotionType.FIXED: self._ui.fixedRadio,
            PointMotionType.SLIP: self._ui.slipRadio,
            PointMotionType.PRESCRIBED_MOTION: self._ui.prescribedMotionRadio,
        }

        for pmt, radio in self._radioMap.items():
            self._buttonGroup.addButton(radio)
            if pmt not in allowedTypes:
                radio.setEnabled(False)

        self._radioMap[currentType].setChecked(True)

        self._ui.buttonBox.accepted.connect(self.accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @property
    def selectedType(self) -> PointMotionType:
        for pmt, radio in self._radioMap.items():
            if radio.isChecked():
                return pmt
        return PointMotionType.FIXED


class PointMotionDialog(QDialog):
    def __init__(self, parent, entry: MovingBoundaryEntry):
        super().__init__(parent)

        self._ui = Ui_PointMotionDialog()
        self._ui.setupUi(self)

        self._entry = entry
        self._pointMotionType = entry.pointMotionType
        self._motionFunctions = [deepcopy(mf) for mf in entry.motionFunctions]
        self._rigidBodyMotion = deepcopy(entry.rigidBodyMotion)

        # Normal vector
        self._ui.normalGroup.setChecked(entry.useFixedNormal)
        self._ui.normal.setVector(entry.normal)

        # Add motion function menu
        addMenu = QMenu(self._ui.addMfButton)
        for ft in [MotionFunctionType.ROTATION, MotionFunctionType.ROTATING_OSCILLATION,
                    MotionFunctionType.LINEAR_TRANSLATION, MotionFunctionType.LINEAR_OSCILLATION,
                    MotionFunctionType.MANUAL_POSITION]:
            action = addMenu.addAction(FUNCTION_TYPE_NAMES[ft])
            action.triggered.connect(lambda checked=False, ftype=ft: self._addMotionFunction(ftype))
        self._ui.addMfButton.setMenu(addMenu)

        self._connectSignalsSlots()
        self._updatePage()
        self._loadMotionFunctions()

    def _connectSignalsSlots(self):
        self._ui.changeButton.clicked.connect(self._changeType)
        self._ui.mfList.customContextMenuRequested.connect(self._showMfContextMenu)
        self._ui.mfList.itemDoubleClicked.connect(self._editMf)
        self._ui.editRigidBodyButton.clicked.connect(self._editRigidBodyMotion)
        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    def _updatePage(self):
        self._ui.typeLabel.setText(POINT_MOTION_TYPE_NAMES[self._pointMotionType])
        if self._pointMotionType == PointMotionType.SLIP:
            self._ui.stack.setCurrentWidget(self._ui.slipPage)
        elif self._pointMotionType == PointMotionType.PRESCRIBED_MOTION:
            self._ui.stack.setCurrentWidget(self._ui.prescribedPage)
        elif self._pointMotionType == PointMotionType.RIGID_BODY_MOTION:
            self._ui.stack.setCurrentWidget(self._ui.rigidBodyPage)
        else:
            self._ui.stack.setCurrentWidget(self._ui.emptyPage)

    def _changeType(self):
        allowedTypes = set(PointMotionType)

        db = coredb.CoreDB()
        xpath = BoundaryDB.getXPath(self._entry.boundary)
        if not (WallMotion(db.getValue(xpath + '/wall/velocity/wallMotion/type')) == WallMotion.MOVING_WALL
                and MovingWallMotion(db.getValue(xpath + '/wall/velocity/wallMotion/movingWall/motion')) == MovingWallMotion.MESH_MOTION):
            allowedTypes.discard(PointMotionType.PRESCRIBED_MOTION)
            allowedTypes.discard(PointMotionType.RIGID_BODY_MOTION)

        self._dialog = PointMotionTypeDialog(self, self._pointMotionType, allowedTypes)
        self._dialog.accepted.connect(self._typeChanged)
        self._dialog.open()

    def _typeChanged(self):
        self._pointMotionType = self._dialog.selectedType
        self._updatePage()

    def _loadMotionFunctions(self):
        self._ui.mfList.clear()
        for mf in self._motionFunctions:
            widget = MotionFunctionWidget(mf)
            item = QListWidgetItem()
            item.setSizeHint(widget.size())
            self._ui.mfList.addItem(item)
            self._ui.mfList.setItemWidget(item, widget)

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

    def _showMfContextMenu(self, pos):
        row = self._ui.mfList.currentRow()
        if row < 0:
            return
        menu = QMenu(self)
        if row > 0:
            menu.addAction(self.tr('Move Up')).triggered.connect(lambda: self._moveMf(row, row - 1))
        if row < self._ui.mfList.count() - 1:
            menu.addAction(self.tr('Move Down')).triggered.connect(lambda: self._moveMf(row, row + 1))
        menu.addAction(self.tr('Edit')).triggered.connect(self._editMf)
        menu.addAction(self.tr('Remove')).triggered.connect(self._removeMf)
        menu.exec(self._ui.mfList.mapToGlobal(pos))

    def _moveMf(self, fromRow, toRow):
        self._motionFunctions[fromRow], self._motionFunctions[toRow] = \
            self._motionFunctions[toRow], self._motionFunctions[fromRow]
        self._loadMotionFunctions()
        self._ui.mfList.setCurrentRow(toRow)

    def _editMf(self):
        row = self._ui.mfList.currentRow()
        if row < 0:
            return
        mf = self._motionFunctions[row]
        dialogClass = MOTION_FUNCTION_DIALOGS.get(mf.functionType)
        if dialogClass:
            self._dialog = dialogClass(self, mf)
            self._dialog.accepted.connect(lambda: self._mfEdited(row))
            self._dialog.open()

    def _mfEdited(self, row):
        widget = self._ui.mfList.itemWidget(self._ui.mfList.item(row))
        if isinstance(widget, MotionFunctionWidget):
            widget.load()

    def _removeMf(self):
        row = self._ui.mfList.currentRow()
        if row >= 0:
            del self._motionFunctions[row]
            self._ui.mfList.takeItem(row)

    def _editRigidBodyMotion(self):
        from baramFlow.view.setup.dynamic_mesh.moving_boundary.rigid_body_motion_dialog import RigidBodyMotionDialog
        self._dialog = RigidBodyMotionDialog(self, self._rigidBodyMotion)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _accept(self):
        if self._pointMotionType == PointMotionType.PRESCRIBED_MOTION and not self._motionFunctions:
            await AsyncMessageBox().warning(self, self.tr('Warning'),
                                            self.tr('At least one motion function must be defined.'))
            return

        for i, mf in enumerate(self._motionFunctions):
            mf.order = i + 1

        try:
            normal = self._ui.normal.vector(self.tr('Normal'))
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._entry.pointMotionType = self._pointMotionType
        self._entry.useFixedNormal = self._ui.normalGroup.isChecked()
        self._entry.normal = normal
        self._entry.motionFunctions = self._motionFunctions
        self._entry.rigidBodyMotion = self._rigidBodyMotion

        EventBus().onConfigChanged.emit()

        self.accept()
