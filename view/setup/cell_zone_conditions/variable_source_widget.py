#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget

from view.widgets.number_input_dialog import PiecewiseLinearDialog, PolynomialDialog
from .variable_source_widget_ui import Ui_VariableSourceWidget


class TemporalProfileType(Enum):
    CONSTANT = 0
    PIECEWISE_LINEAR = auto()
    POLYNOMIAL = auto()


class VariableSourceWidget(QWidget):
    def __init__(self, title):
        super().__init__()
        self._ui = Ui_VariableSourceWidget()
        self._ui.setupUi(self)

        self._ui.groupBox.setTitle(title)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.groupBox.toggled.connect(self._toggled)
        self._ui.temporalProfileType.currentIndexChanged.connect(self._temporalProfileTypeChanged)
        self._ui.edit.clicked.connect(self._edit)

    def _toggled(self, on):
        if on:
            self._temporalProfileTypeChanged(self._ui.temporalProfileType.currentIndex())

    def _temporalProfileTypeChanged(self, index):
        self._ui.edit.setEnabled(index != TemporalProfileType.CONSTANT.value)
        self._ui.constantValue.setEnabled(index == TemporalProfileType.CONSTANT.value)

    def _edit(self):
        temporalProfileType = self._ui.temporalProfileType.currentIndex()
        if temporalProfileType == TemporalProfileType.PIECEWISE_LINEAR.value:
            if self._ui.groupBox.title() == "Energy":
                dialog = PiecewiseLinearDialog(self.tr("Piecewise Linear"), [self.tr("t"), self.tr("Energy")], ["", ""])
                dialog.exec()
            else:
                dialog = PiecewiseLinearDialog(
                    self.tr("Piecewise Linear"), [self.tr("t"), self.tr("Flow Rate")], ["", ""])
                dialog.exec()
        elif temporalProfileType == TemporalProfileType.POLYNOMIAL.value:
            dialog = PolynomialDialog(self.tr("Polynomial"), "")
            dialog.exec()
