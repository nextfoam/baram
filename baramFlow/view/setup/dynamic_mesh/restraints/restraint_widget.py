#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.base.dynamic_mesh.restraint import Restraint, RestraintType

from .restraint_widget_ui import Ui_RestraintWidget


RESTRAINT_TYPE_NAMES = {
    RestraintType.SIMPLE_DAMPER: 'Damper',
    RestraintType.TRANSLATIONAL_SPRING: 'Spring',
    RestraintType.ROTATIONAL_SPRING: 'R.Spring',
}


class RestraintWidget(QWidget):
    def __init__(self, restraint: Restraint):
        super().__init__()

        self._restraint = restraint

        self._ui = Ui_RestraintWidget()
        self._ui.setupUi(self)

        self.setFixedHeight(48)
        self.load()

    @property
    def restraint(self) -> Restraint:
        return self._restraint

    def load(self):
        r = self._restraint
        self._ui.nameLabel.setText(RESTRAINT_TYPE_NAMES.get(r.restraintType, str(r.restraintType.value)))

        if r.restraintType == RestraintType.SIMPLE_DAMPER:
            self._ui.detailLabel.setText(f'{r.dampingConstant} Ns/m')
        elif r.restraintType == RestraintType.TRANSLATIONAL_SPRING:
            self._ui.detailLabel.setText(f'{r.restLength} m')
        elif r.restraintType == RestraintType.ROTATIONAL_SPRING:
            self._ui.detailLabel.setText(str(r.axis))
