#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from widgets.enum_button_group import EnumButtonGroup
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.boundary.boundary import PatchInteractionType
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from .patch_interaction_widget_ui import Ui_PatchInteractionWidget


class PatchInteractionWidget(QWidget):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_PatchInteractionWidget()
        self._ui.setupUi(self)

        self._typeRadios = EnumButtonGroup()

        self._bcid = bcid

        self._data = None
        self._recycleBoundary = None

        self._typeRadios.addEnumButton(self._ui.none,       PatchInteractionType.NONE)
        self._typeRadios.addEnumButton(self._ui.reflect,    PatchInteractionType.REFLECT)
        self._typeRadios.addEnumButton(self._ui.escape,     PatchInteractionType.ESCAPE)
        self._typeRadios.addEnumButton(self._ui.trap,       PatchInteractionType.TRAP)
        self._typeRadios.addEnumButton(self._ui.recycle,    PatchInteractionType.RECYCLE)

        self._connectSignalsSlots()

    def setData(self, data):
        self._data = data
        self._typeRadios.setCheckedData(data.type)
        self._ui.normal.setBatchableNumber(data.reflect.normal)
        self._ui.tangential.setBatchableNumber(data.reflect.tangential)
        self._setRecycleBoundary(data.recycle.recycleBoundary)
        self._ui.recycleFraction.setBatchableNumber(data.recycle.recycleFraction)

    def updateData(self):
        self._data.type = self._typeRadios.checkedData()
        if self._data.type == PatchInteractionType.REFLECT:
            self._data.reflect.normal = self._ui.normal.batchableNumber()
            self._data.reflect.tangential = self._ui.tangential.batchableNumber()
        elif self._data.type == PatchInteractionType.RECYCLE:
            self._data.recycle.recycleBoundary = self._recycleBoundary
            self._data.recycle.recycleFraction = self._ui.recycleFraction.batchableNumber()

        return self._data

    def validate(self):
        type_ = self._typeRadios.checkedData()
        if type_ == PatchInteractionType.REFLECT:
            self._ui.normal.validate(self.tr('Normal'), low=0, high=1)
            self._ui.tangential.validate(self.tr('Tangential'), low=0, high=1)
        elif type_ == PatchInteractionType.RECYCLE:
            if self._recycleBoundary == '0':
                raise ValueError(self.tr('Select Recycle Boundary.'))

            self._ui.recycleFraction.validate(self.tr('Recycle Fraction'), low=0, high=1)

    def _connectSignalsSlots(self):
        self._typeRadios.dataChecked.connect(self._typeChanged)
        self._ui.selectBoundary.clicked.connect(self._openBoundarySelector)

    def _setRecycleBoundary(self, bcid):
        self._recycleBoundary = bcid
        if self._recycleBoundary != '0':
            self._ui.recycleBoundary.setText(BoundaryDB.getBoundaryName(self._recycleBoundary))

    def _typeChanged(self, type_):
        # type_ = self._typeRadios.checkedData()
        self._ui.coefficientOfResititution.setEnabled(type_ == PatchInteractionType.REFLECT)
        self._ui.recycleParameters.setEnabled(type_ == PatchInteractionType.RECYCLE)

    def _openBoundarySelector(self):
        def boundarySelected():
            self._setRecycleBoundary(self._dialog.selectedItem())

        self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Recycle Boundary"),
                                      BoundaryDB.getBoundarySelectorItems([BoundaryType.WALL]),
                                      exclude=self._bcid)
        self._dialog.accepted.connect(boundarySelected)
        self._dialog.open()
