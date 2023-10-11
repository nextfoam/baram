#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Flag, Enum, auto

from PySide6.QtWidgets import QFormLayout

from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .radiation_dialog_ui import Ui_RadiationDialog


class Mode(Flag):
    OFF = auto()
    P1 = auto()
    DO = auto()


class Parameter(Enum):
    FLOW_ITERATIONS = 0
    ABSORPTION_COEFFICIENT = auto()
    PHI_DIVISIONS = auto()
    THETA_DIVISIONS = auto()
    RESIDUAL_CONVERGENCE_CRITERIA = auto()
    MAXIMUM_NUMBER_OF_ITERATIONS = auto()


class RadiationDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_RadiationDialog()
        self._ui.setupUi(self)
        self._form = self._ui.parametersGroup.layout()

        self._ui.modelRadioGroup.setId(self._ui.off, Mode.OFF.value)
        self._ui.modelRadioGroup.setId(self._ui.p1, Mode.P1.value)
        self._ui.modelRadioGroup.setId(self._ui.DO, Mode.DO.value)

        self._parameters = []
        self._parameters.append([Mode.P1 | Mode.DO, *self._getRowWidgets(Parameter.FLOW_ITERATIONS.value)])
        self._parameters.append([Mode.P1 | Mode.DO, *self._getRowWidgets(Parameter.ABSORPTION_COEFFICIENT.value)])
        self._parameters.append([          Mode.DO, *self._getRowWidgets(Parameter.PHI_DIVISIONS.value)])
        self._parameters.append([          Mode.DO, *self._getRowWidgets(Parameter.THETA_DIVISIONS.value)])
        self._parameters.append([          Mode.DO, *self._getRowWidgets(Parameter.RESIDUAL_CONVERGENCE_CRITERIA.value)])
        self._parameters.append([          Mode.DO, *self._getRowWidgets(Parameter.MAXIMUM_NUMBER_OF_ITERATIONS.value)])

        self.connectSignalsSlots()

    def connectSignalsSlots(self):
        self._ui.modelRadioGroup.idToggled.connect(self._modelChanged)

    def _removeAll(self):
        for _ in range(self._form.rowCount()):
            labelItem = self._form.itemAt(0, QFormLayout.LabelRole)
            fieldItem = self._form.itemAt(0, QFormLayout.FieldRole)
            label = labelItem.widget()
            field = fieldItem.widget()
            self._form.removeItem(labelItem)
            self._form.removeItem(fieldItem)
            self._form.removeRow(0)
            label.setParent(None)
            field.setParent(None)

    def _modelChanged(self, mode, checked):
        if checked:
            self._removeAll()
            self._showParams(Mode(mode))
            self._ui.parametersWidget.setVisible(mode != Mode.OFF.value)

    def _showParams(self, flag):
        for p in self._parameters:
            if p[0] & flag:
                self._form.addRow(p[1], p[2])

    def _getRowWidgets(self, row):
        return (self._form.itemAt(row, QFormLayout.LabelRole).widget(),
                self._form.itemAt(row, QFormLayout.FieldRole).widget())
