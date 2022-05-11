#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from enum import Enum, auto

from .variable_source_widget_ui import Ui_VariableSourceWidget


class VariableSourceWidget(QWidget):
    class TEMPORAL_PROFILE_TYPE(Enum):
        CONSTANT = 0
        PIECEWISE_LINEAR_DIRECT_INPUT = auto()
        PIECEWISE_LINEAR_CSV_FILE_UPLOAD = auto()
        POLYNOMIAL_DIRECT_INPUT = auto()

    def __init__(self, title):
        super().__init__()
        self._ui = Ui_VariableSourceWidget()
        self._ui.setupUi(self)

        self._ui.groupBox.setTitle(title)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.groupBox.toggled.connect(self._toggled)
        self._ui.temporalProfileType.currentIndexChanged.connect(self._temporalProfileTypeChanged)

    def _toggled(self, on):
        if on:
            self._temporalProfileTypeChanged(self._ui.temporalProfileType.currentIndex())

    def _temporalProfileTypeChanged(self, index):
        self._ui.edit.setEnabled(
            index == self.TEMPORAL_PROFILE_TYPE.PIECEWISE_LINEAR_DIRECT_INPUT.value
            or index == self.TEMPORAL_PROFILE_TYPE.POLYNOMIAL_DIRECT_INPUT.value
        )
        self._ui.constantValue.setEnabled(index == self.TEMPORAL_PROFILE_TYPE.CONSTANT.value)
        self._ui.fileName.setEnabled(False)
        self._ui.browse.setEnabled(
            index == self.TEMPORAL_PROFILE_TYPE.PIECEWISE_LINEAR_CSV_FILE_UPLOAD.value
        )
