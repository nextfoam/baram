#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.base.dynamic_mesh.motion_function import MotionFunction, MotionFunctionType

from .motion_function_widget_ui import Ui_MotionFunctionWidget


FUNCTION_TYPE_NAMES = {
    MotionFunctionType.ROTATION: 'Rotation',
    MotionFunctionType.ROTATING_OSCILLATION: 'Rotating Oscillation',
    MotionFunctionType.LINEAR_TRANSLATION: 'Linear Translation',
    MotionFunctionType.LINEAR_OSCILLATION: 'Linear Oscillation',
    MotionFunctionType.MANUAL_POSITION: 'Manual Position',
}


class MotionFunctionWidget(QWidget):
    def __init__(self, motionFunction: MotionFunction):
        super().__init__()

        self._motionFunction = motionFunction

        self._ui = Ui_MotionFunctionWidget()
        self._ui.setupUi(self)

        self.setFixedHeight(48)
        self.load()

    @property
    def motionFunction(self) -> MotionFunction:
        return self._motionFunction

    def load(self):
        f = self._motionFunction
        self._ui.nameLabel.setText(FUNCTION_TYPE_NAMES.get(f.functionType, str(f.functionType.value)))

        detail = ''
        if f.functionType == MotionFunctionType.ROTATION:
            detail = f'{f.rpm} rpm'
        elif f.functionType == MotionFunctionType.ROTATING_OSCILLATION:
            detail = f'{f.rpm} rpm'
        elif f.functionType == MotionFunctionType.LINEAR_TRANSLATION:
            detail = f'{f.velocity} m/s'
        elif f.functionType == MotionFunctionType.LINEAR_OSCILLATION:
            detail = f'{f.frequency} Hz'
        elif f.functionType == MotionFunctionType.MANUAL_POSITION:
            detail = 'Manual Positions'

        self._ui.detailLabel.setText(detail)
