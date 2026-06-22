#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog

from baramFlow.base.dynamic_mesh.rigid_body_dynamics import Joint, JointType
from baramFlow.base.event_bus import EventBus
from widgets.async_message_box import AsyncMessageBox

from .prismatic_joint_dialog_ui import Ui_PrismaticJointDialog
from .revolute_joint_dialog_ui import Ui_RevoluteJointDialog


class PrismaticJointDialog(QDialog):
    def __init__(self, parent, joint: Joint):
        super().__init__(parent)
        self._ui = Ui_PrismaticJointDialog()
        self._ui.setupUi(self)
        self._joint = joint

        self._ui.direction.setVector(joint.direction)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            direction = self._ui.direction.vector('Direction')
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._joint.direction = direction

        EventBus().onConfigChanged.emit()

        self.accept()


class RevoluteJointDialog(QDialog):
    def __init__(self, parent, joint: Joint):
        super().__init__(parent)
        self._ui = Ui_RevoluteJointDialog()
        self._ui.setupUi(self)
        self._joint = joint

        self._ui.axis.setVector(joint.axis)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            axis = self._ui.axis.vector('Axis')
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._joint.axis = axis

        EventBus().onConfigChanged.emit()

        self.accept()


JOINT_DIALOGS = {
    JointType.PRISMATIC: PrismaticJointDialog,
    JointType.REVOLUTE: RevoluteJointDialog,
}
