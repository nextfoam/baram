#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QButtonGroup
import qasync

from baramFlow.base.dynamic_mesh.dynamic_mesh import MotionType
from baramFlow.base.event_bus import EventBus

from .motion_type_dialog_ui import Ui_MotionTypeDialog


class MotionTypeDialog(QDialog):
    def __init__(self, parent, currentType: MotionType):
        super().__init__(parent)

        self._ui = Ui_MotionTypeDialog()
        self._ui.setupUi(self)

        self._buttonGroup = QButtonGroup(self)
        self._buttonGroup.addButton(self._ui.noneRadio)
        self._buttonGroup.addButton(self._ui.movingCellZoneRadio)
        self._buttonGroup.addButton(self._ui.movingBoundaryRadio)
        self._buttonGroup.addButton(self._ui.rigidBodyDynamicsRadio)

        self._radioMap = {
            MotionType.NONE: self._ui.noneRadio,
            MotionType.MOVING_CELL_ZONE: self._ui.movingCellZoneRadio,
            MotionType.MOVING_BOUNDARY: self._ui.movingBoundaryRadio,
            MotionType.RIGID_BODY_DYNAMICS: self._ui.rigidBodyDynamicsRadio,
        }

        self._radioMap[currentType].setChecked(True)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @property
    def selectedType(self) -> MotionType:
        for motionType, radio in self._radioMap.items():
            if radio.isChecked():
                return motionType
        return MotionType.NONE

    @qasync.asyncSlot()
    async def _accept(self):
        EventBus().onConfigChanged.emit()

        self.accept()
