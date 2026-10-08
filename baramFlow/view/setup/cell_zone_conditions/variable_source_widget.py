#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
from copy import deepcopy

import qasync
from PySide6.QtWidgets import QWidget

from baramFlow.base.base import NumberList, TemporalScalarList
from baramFlow.base.cell_zone.cell_zone import SpecificationMethod, TemporalProfileType, VariableSourceTerm
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.view.widgets.number_input_dialog import PolynomialDialog
from widgets.simple_sheet_dialog import SimpleSheetDialog
from .variable_source_widget_ui import Ui_VariableSourceWidget


class VariableSourceWidget(QWidget):
    def __init__(self, title: str, data: VariableSourceTerm | None, units: dict[SpecificationMethod, str] = None):
        super().__init__()
        self._ui = Ui_VariableSourceWidget()
        self._ui.setupUi(self)

        self._title: str = title
        self._units: dict[SpecificationMethod, str] = units
        self._data: VariableSourceTerm = data or VariableSourceTerm()

        self._piecewiseLinear: TemporalScalarList = self._data.piecewiseLinear
        self._polynomial: NumberList = self._data.polynomial

        self._ui.groupBox.setTitle(title)
        self._ui.specificationMethod.addItem(self.tr("Value per Unit Volume"),
                                             SpecificationMethod.VALUE_PER_UNIT_VOLUME)
        self._ui.specificationMethod.addItem(self.tr("Value for Entire Cell Zone"),
                                             SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE)

        self._ui.temporalProfileType.addItem(self.tr("Constant"),           TemporalProfileType.CONSTANT)
        self._ui.temporalProfileType.addItem(self.tr("Piecewise Linear"),   TemporalProfileType.PIECEWISE_LINEAR)
        self._ui.temporalProfileType.addItem(self.tr("Polynomial"),         TemporalProfileType.POLYNOMIAL)

        self._connectSignalsSlots()

    def setChecked(self, checked):
        self._ui.groupBox.setChecked(checked)

    def load(self):
        self._ui.groupBox.setChecked(not self._data.disabled)
        self._ui.specificationMethod.setCurrentIndex(self._ui.specificationMethod.findData(self._data.unit))

        if GeneralDB.isTimeTransient():
            self._ui.temporalProfileType.setCurrentIndex(
                self._ui.temporalProfileType.findData(self._data.specification))
            self._ui.temporalProfileType.setEnabled(True)
        else:
            self._ui.temporalProfileType.setCurrentIndex(
                self._ui.temporalProfileType.findData(TemporalProfileType.CONSTANT))
            self._ui.temporalProfileType.setEnabled(False)

        self._ui.constantValue.setPFloat(self._data.constant)

        self._onSpecificationMethodChanged()
        self._onTemporalProfileTypeChanged()

    def data(self):
        data = deepcopy(self._data)
        data.disabled = not self._ui.groupBox.isChecked()
        if data.disabled:
            return data

        data.unit = self._ui.specificationMethod.currentData()
        data.specification = self._ui.temporalProfileType.currentData()
        if data.specification == TemporalProfileType.CONSTANT:
            data.constant = self._ui.constantValue.pFloat(self.tr('{} Value').format(self._title))
        elif data.specification == TemporalProfileType.PIECEWISE_LINEAR:
            if self._piecewiseLinear is None:
                raise ValueError(self.tr('Edit {} Piecewise Linear Values.').format(self._title))

            data.piecewiseLinear = self._piecewiseLinear
        elif data.specification == TemporalProfileType.POLYNOMIAL:
            if self._polynomial is None:
                raise ValueError(self.tr('Edit {} Polynomial Values.').format(self._title))

            data.polynomial = self._polynomial

        return data

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._onSpecificationMethodChanged)
        self._ui.temporalProfileType.currentIndexChanged.connect(self._onTemporalProfileTypeChanged)
        self._ui.edit.clicked.connect(self._edit)

    def _onSpecificationMethodChanged(self):
        if self._units:
            self._ui.label.setText(
                self.tr('Value') + f' ({self._units.get(self._ui.specificationMethod.currentData(), "")})')

    def _onTemporalProfileTypeChanged(self):
        temporalProfileType = self._ui.temporalProfileType.currentData()
        self._ui.edit.setEnabled(temporalProfileType != TemporalProfileType.CONSTANT)
        self._ui.constantValue.setEnabled(temporalProfileType == TemporalProfileType.CONSTANT)

    @qasync.asyncSlot()
    async def _edit(self):
        def updatePolynomial(data: list[str]):
            self._polynomial = NumberList(values=data)

        temporalProfileType = self._ui.temporalProfileType.currentData()
        if temporalProfileType == TemporalProfileType.PIECEWISE_LINEAR:
            dialog = SimpleSheetDialog(self, self.tr('Piecewise Linear'), [self.tr("t"), self._title],
                                       self._piecewiseLinear.data())
            try:
                self._piecewiseLinear = TemporalScalarList(await dialog.show())
            except asyncio.exceptions.CancelledError:
                return
        elif temporalProfileType == TemporalProfileType.POLYNOMIAL:
            self._dialog = PolynomialDialog(self, self.tr("Polynomial"), self._polynomial.values)
            self._dialog.dataAccepted.connect(updatePolynomial)
            self._dialog.open()

    def _piecewiseLinearAccepted(self):
        self._piecewiseLinear = self._dialog.getValues()
