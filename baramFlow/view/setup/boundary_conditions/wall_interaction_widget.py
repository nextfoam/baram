#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from widgets.enum_button_group import EnumButtonGroup

from baramFlow.base.boundary.boundary import WallInteractionType
from .wall_interaction_widget_ui import Ui_WallInteractionWidget


class WallInteractionWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_WallInteractionWidget()
        self._ui.setupUi(self)

        self._data = None

        self._typeRadios = EnumButtonGroup()

        self._typeRadios.addEnumButton(self._ui.none,       WallInteractionType.NONE)
        self._typeRadios.addEnumButton(self._ui.reflect,    WallInteractionType.REFLECT)
        self._typeRadios.addEnumButton(self._ui.escape,     WallInteractionType.ESCAPE)
        self._typeRadios.addEnumButton(self._ui.trap,       WallInteractionType.TRAP)
        self._typeRadios.addEnumButton(self._ui.recycle,    WallInteractionType.RECYCLE)

        self._connectSignalsSlots()

    def setData(self, data):
        self._data = data
        self._typeRadios.setCheckedData(data.type)
        self._ui.normal.setBatchableNumber(data.reflect.normal)
        self._ui.tangential.setBatchableNumber(data.reflect.tangential)
        self._ui.recycleBoundary.setBatchableNumber(data.recycle.recycleBoundary)
        self._ui.recycleFraction.setBatchableNumber(data.recycle.recycleFraction)

    def updateData(self):
        self._data.type = self._typeRadios.checkedData()
        if self._data.type == WallInteractionType.REFLECT:
            self._data.reflect.normal = self._ui.normal.batchableNumber()
            self._data.reflect.tangential = self._ui.tangential.batchableNumber()
        elif self._data.type == WallInteractionType.RECYCLE:
            self._data.recycle.recycleBoundary = self._ui.recycleBoundary.batchableNumber()
            self._data.recycle.recycleFraction = self._ui.recycleFraction.batchableNumber()

        return self._data

    def validate(self):
        type_ = self._typeRadios.checkedData()
        if type_ == WallInteractionType.REFLECT:
            self._ui.normal.validate(self.tr('Normal'), low=0, high=1)
            self._ui.tangential.validate(self.tr('Tangential'), low=0, high=1)
        elif type_ == WallInteractionType.RECYCLE:
            self._ui.recycleBoundary.validate(self.tr('Recycle Boundary'))
            self._ui.recycleFraction.validate(self.tr('Recycle Fraction'), low=0, high=1)

    def _connectSignalsSlots(self):
        self._typeRadios.dataChecked.connect(self._typeChanged)

    def _typeChanged(self, type_):
        # type_ = self._typeRadios.checkedData()
        self._ui.coefficientOfResititution.setEnabled(type_ == WallInteractionType.REFLECT)
        self._ui.recycleParameters.setEnabled(type_ == WallInteractionType.RECYCLE)