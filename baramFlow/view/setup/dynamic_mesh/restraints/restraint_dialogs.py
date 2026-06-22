#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog

from baramFlow.base.dynamic_mesh.restraint import Restraint, RestraintType
from baramFlow.base.event_bus import EventBus
from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from .simple_damper_dialog_ui import Ui_SimpleDamperDialog
from .translational_spring_dialog_ui import Ui_TranslationalSpringDialog
from .rotational_spring_dialog_ui import Ui_RotationalSpringDialog


class SimpleDamperDialog(QDialog):
    def __init__(self, parent, restraint: Restraint):
        super().__init__(parent)
        self._ui = Ui_SimpleDamperDialog()
        self._ui.setupUi(self)
        self._restraint = restraint

        self._ui.dampingConstant.setPFloat(restraint.dampingConstant)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            dampingConstant = self._ui.dampingConstant.pFloat(self.tr('Damping Constant'))
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._restraint.dampingConstant = dampingConstant

        EventBus().onConfigChanged.emit()

        self.accept()


class TranslationalSpringDialog(QDialog):
    def __init__(self, parent, restraint: Restraint):
        super().__init__(parent)
        self._ui = Ui_TranslationalSpringDialog()
        self._ui.setupUi(self)
        self._restraint = restraint

        self._ui.attachmentPoint.setVector(restraint.attachmentPoint)
        self._ui.anchorPoint.setVector(restraint.anchorPoint)
        self._ui.restLength.setPFloat(restraint.restLength)
        self._ui.springConstant.setPFloat(restraint.springConstant)
        self._ui.dampingConstant.setPFloat(restraint.dampingConstant)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            attachmentPoint = self._ui.attachmentPoint.vector('Attachment Point')
            anchorPoint = self._ui.anchorPoint.vector('Anchor Point')
            restLength = self._ui.restLength.pFloat(self.tr('Rest Length'), low=0)
            springConstant = self._ui.springConstant.pFloat(self.tr('Spring Constant'))
            dampingConstant = self._ui.dampingConstant.pFloat(self.tr('Damping Constant'))
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._restraint.attachmentPoint = attachmentPoint
        self._restraint.anchorPoint = anchorPoint
        self._restraint.restLength = restLength
        self._restraint.springConstant = springConstant
        self._restraint.dampingConstant = dampingConstant

        EventBus().onConfigChanged.emit()

        self.accept()


class RotationalSpringDialog(QDialog):
    def __init__(self, parent, restraint: Restraint, showOrientation=True):
        super().__init__(parent)
        self._ui = Ui_RotationalSpringDialog()
        self._ui.setupUi(self)
        self._restraint = restraint
        self._showOrientation = showOrientation

        self._ui.axis.setVector(restraint.axis)
        self._ui.springConstant.setPFloat(restraint.springConstant)
        self._ui.dampingConstant.setPFloat(restraint.dampingConstant)

        if showOrientation:
            self._ui.useBoundaryOrientation.setChecked(restraint.useBoundaryOrientation)
            oriEdits = [
                [self._ui.ori00, self._ui.ori01, self._ui.ori02],
                [self._ui.ori10, self._ui.ori11, self._ui.ori12],
                [self._ui.ori20, self._ui.ori21, self._ui.ori22],
            ]
            for i in range(3):
                for j in range(3):
                    oriEdits[i][j].setPFloat(restraint.orientation[i * 3 + j])
            self._ui.privateOrientation.setEnabled(not restraint.useBoundaryOrientation)

            self._ui.useBoundaryOrientation.toggled.connect(
                lambda checked: self._ui.privateOrientation.setEnabled(not checked))
        else:
            self._ui.orientation.setVisible(False)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            axis = self._ui.axis.vector('Axis')
            springConstant = self._ui.springConstant.pFloat(self.tr('Spring Constant'), low=0)
            dampingConstant = self._ui.dampingConstant.pFloat(self.tr('Damping Constant'), low=0)

            if self._showOrientation:
                useBoundaryOrientation = self._ui.useBoundaryOrientation.isChecked()

                oriEdits = [
                    [self._ui.ori00, self._ui.ori01, self._ui.ori02],
                    [self._ui.ori10, self._ui.ori11, self._ui.ori12],
                    [self._ui.ori20, self._ui.ori21, self._ui.ori22],
                ]
                orientation: list[PFloat] = []
                for i in range(3):
                    for j in range(3):
                        orientation.append(oriEdits[i][j].pFloat(self.tr('Orientation')))

        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._restraint.axis = axis
        self._restraint.springConstant = springConstant
        self._restraint.dampingConstant = dampingConstant
        if self._showOrientation:
            self._restraint.useBoundaryOrientation = useBoundaryOrientation
            self._restraint.orientation = orientation

        EventBus().onConfigChanged.emit()

        self.accept()


RESTRAINT_DIALOGS = {
    RestraintType.SIMPLE_DAMPER: SimpleDamperDialog,
    RestraintType.TRANSLATIONAL_SPRING: TranslationalSpringDialog,
    RestraintType.ROTATIONAL_SPRING: RotationalSpringDialog,
}
