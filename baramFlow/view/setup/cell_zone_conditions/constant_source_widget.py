#!/usr/bin/env python
# -*- coding: utf-8 -*-
from copy import deepcopy

from PySide6.QtWidgets import QWidget

from baramFlow.base.cell_zone.cell_zone import SpecificationMethod, ConstantSourceTerm
from .constant_source_widget_ui import Ui_ConstantSourceWidget


class ConstantSourceWidget(QWidget):
    def __init__(self, title: str, label: str, units: dict[SpecificationMethod, str], data: ConstantSourceTerm):
        super().__init__()
        self._ui = Ui_ConstantSourceWidget()
        self._ui.setupUi(self)

        self._title: str = title
        self._label: str = label
        self._units = units
        self._data: ConstantSourceTerm = data or ConstantSourceTerm()

        self._ui.groupBox.setTitle(title)
        self._ui.label.setText(label)

        self._ui.specificationMethod.addItem(self.tr("Value per Unit Volume"),
                                             SpecificationMethod.VALUE_PER_UNIT_VOLUME)
        self._ui.specificationMethod.addItem(self.tr("Value for Entire Cell Zone"),
                                             SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE)

        self._connectSignalsSlots()

    def load(self):
        self._ui.groupBox.setChecked(not self._data.disabled)
        self._ui.specificationMethod.setCurrentIndex(self._ui.specificationMethod.findData(self._data.unit))
        self._ui.value.setPFloat(self._data.constant)

        self._onSpecificationMethodChanged()

    def data(self):
        data = deepcopy(self._data)
        data.disabled = not self._ui.groupBox.isChecked()
        if data.disabled:
            return data

        data.unit = self._ui.specificationMethod.currentData()
        data.constant = self._ui.value.pFloat(self.tr('{} Value').format(self._title))

        return data

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._onSpecificationMethodChanged)

    def _onSpecificationMethodChanged(self):
        self._ui.label.setText(f'{self._label} ({self._units.get(self._ui.specificationMethod.currentData(), "")})')
