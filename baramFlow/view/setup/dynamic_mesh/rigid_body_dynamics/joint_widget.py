#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.base.dynamic_mesh.rigid_body_dynamics import Joint, JointType

from .joint_widget_ui import Ui_JointWidget


JOINT_TYPE_NAMES = {
    JointType.PRISMATIC: 'Prismatic',
    JointType.REVOLUTE: 'Revolute',
    JointType.SPHERICAL: 'Spherical',
}

PRISMATIC_HINTS = {'1 0 0': 'Surge', '0 1 0': 'Sway', '0 0 1': 'Heave'}
REVOLUTE_HINTS = {'1 0 0': 'Roll', '0 1 0': 'Pitch', '0 0 1': 'Yaw'}


def _directionHint(joint: Joint) -> str:
    if joint.jointType == JointType.PRISMATIC:
        key = f'{joint.direction.x} {joint.direction.y} {joint.direction.z}'
        hint = PRISMATIC_HINTS.get(key, '')
        vec = str(joint.direction)
        return f'{hint} {vec}'.strip() if hint else vec
    elif joint.jointType == JointType.REVOLUTE:
        key = f'{joint.axis.x} {joint.axis.y} {joint.axis.z}'
        hint = REVOLUTE_HINTS.get(key, '')
        vec = str(joint.axis)
        return f'{hint} {vec}'.strip() if hint else vec
    return ''


class JointWidget(QWidget):
    def __init__(self, joint: Joint):
        super().__init__()

        self._joint = joint

        self._ui = Ui_JointWidget()
        self._ui.setupUi(self)

        self.setFixedHeight(48)
        self.load()

    @property
    def joint(self) -> Joint:
        return self._joint

    def load(self):
        self._ui.nameLabel.setText(JOINT_TYPE_NAMES.get(self._joint.jointType, ''))
        self._ui.detailLabel.setText(_directionHint(self._joint))
