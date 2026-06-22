#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

import qasync

from PySide6.QtWidgets import QDialog

from baramFlow.base.dynamic_mesh.motion_function import MotionFunctionType, MotionFunction, Positions
from baramFlow.base.event_bus import EventBus
from widgets.async_message_box import AsyncMessageBox
from widgets.simple_sheet_dialog import SimpleSheetDialog

from .rotation_dialog_ui import Ui_RotationDialog
from .rotating_oscillation_dialog_ui import Ui_RotatingOscillationDialog
from .linear_translation_dialog_ui import Ui_LinearTranslationDialog
from .linear_oscillation_dialog_ui import Ui_LinearOscillationDialog
from .manual_position_dialog_ui import Ui_ManualPositionDialog


class RotationDialog(QDialog):
    def __init__(self, parent, motionFunction: MotionFunction):
        super().__init__(parent)
        self._ui = Ui_RotationDialog()
        self._ui.setupUi(self)
        self._mf = motionFunction

        self._ui.origin.setVector(motionFunction.origin)
        self._ui.axis.setVector(motionFunction.axis)
        self._ui.speed.setPFloat(motionFunction.rpm)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            center = self._ui.origin.vector(self.tr('Origin'))
            axis = self._ui.axis.vector(self.tr('Axis'))
            rpm = self._ui.speed.pFloat(self.tr('Speed'))
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._mf.origin = center
        self._mf.axis = axis
        self._mf.rpm = rpm

        EventBus().onConfigChanged.emit()

        self.accept()


class RotatingOscillationDialog(QDialog):
    def __init__(self, parent, motionFunction: MotionFunction):
        super().__init__(parent)
        self._ui = Ui_RotatingOscillationDialog()
        self._ui.setupUi(self)
        self._mf = motionFunction

        self._ui.origin.setVector(motionFunction.origin)
        self._ui.amplitude.setVector(motionFunction.angularAmplitude)
        self._ui.speed.setPFloat(motionFunction.rpm)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            center = self._ui.origin.vector(self.tr('Origin'))
            angularAmplitude = self._ui.amplitude.vector(self.tr('Amplitude'))
            omega = self._ui.speed.pFloat(self.tr('Speed'))
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._mf.origin = center
        self._mf.angularAmplitude = angularAmplitude
        self._mf.rpm = omega

        EventBus().onConfigChanged.emit()

        self.accept()


class LinearTranslationDialog(QDialog):
    def __init__(self, parent, motionFunction: MotionFunction):
        super().__init__(parent)
        self._ui = Ui_LinearTranslationDialog()
        self._ui.setupUi(self)
        self._mf = motionFunction

        self._ui.velocity.setVector(motionFunction.velocity)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            velocity = self._ui.velocity.vector('Velocity')
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._mf.velocity = velocity

        EventBus().onConfigChanged.emit()

        self.accept()


class LinearOscillationDialog(QDialog):
    def __init__(self, parent, motionFunction: MotionFunction):
        super().__init__(parent)
        self._ui = Ui_LinearOscillationDialog()
        self._ui.setupUi(self)
        self._mf = motionFunction

        self._ui.amplitude.setVector(motionFunction.linearAmplitude)
        self._ui.frequency.setPFloat(motionFunction.frequency)

        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            linearAmplitude = self._ui.amplitude.vector('Amplitude')
            frequency = self._ui.frequency.pFloat(self.tr('Frequency'), low=0, lowInclusive=False)
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._mf.linearAmplitude = linearAmplitude
        self._mf.frequency = frequency

        EventBus().onConfigChanged.emit()

        self.accept()


class ManualPositionDialog(QDialog):
    def __init__(self, parent, motionFunction: MotionFunction):
        super().__init__(parent)
        self._ui = Ui_ManualPositionDialog()
        self._ui.setupUi(self)
        self._mf = motionFunction
        self._positions = self._mf.positions.toRows()

        self._ui.cog.setVector(motionFunction.origin)

        self._ui.positionsButton.clicked.connect(self._handlePositionsButtonClick)
        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _handlePositionsButtonClick(self):
        dialog = SimpleSheetDialog(self, self.tr('Manual Positions'),
                                   [self.tr('t'), self.tr('surge'), self.tr('sway'), self.tr('heave'), self.tr('roll'), self.tr('pitch'), self.tr('yaw')],
                                   self._positions)
        try:
            self._positions = await dialog.show()
        except asyncio.CancelledError:
            return

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            origin = self._ui.cog.vector('Center of Gravity')
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._mf.origin = origin
        self._mf.positions = Positions.fromRows(self._positions)

        EventBus().onConfigChanged.emit()

        self.accept()


MOTION_FUNCTION_DIALOGS = {
    MotionFunctionType.ROTATION: RotationDialog,
    MotionFunctionType.ROTATING_OSCILLATION: RotatingOscillationDialog,
    MotionFunctionType.LINEAR_TRANSLATION: LinearTranslationDialog,
    MotionFunctionType.LINEAR_OSCILLATION: LinearOscillationDialog,
    MotionFunctionType.MANUAL_POSITION: ManualPositionDialog,
}
