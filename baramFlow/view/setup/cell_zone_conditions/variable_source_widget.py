#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import SpecificationMethod, TemporalProfileType
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.view.widgets.number_input_dialog import NumberInputDialog, PolynomialDialog
from widgets.async_message_box import AsyncMessageBox
from .variable_source_widget_ui import Ui_VariableSourceWidget


class VariableSourceWidget(QWidget):
    def __init__(self, title, xpath, units=None):
        super().__init__()
        self._ui = Ui_VariableSourceWidget()
        self._ui.setupUi(self)

        self._title = title
        self._xpath = xpath
        self._piecewiseLinear = None
        self._polynomial = None
        self._units = units

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
        db = coredb.CoreDB()
        if db.exists(self._xpath):
            self._ui.groupBox.setChecked(db.getAttribute(self._xpath, 'disabled') == 'false')
            self._ui.specificationMethod.setCurrentIndex(
                self._ui.specificationMethod.findData(SpecificationMethod(db.getValue(self._xpath + '/unit'))))

            if GeneralDB.isTimeTransient():
                self._ui.temporalProfileType.setCurrentIndex(
                    self._ui.temporalProfileType.findData(
                        TemporalProfileType(db.getValue(self._xpath + '/specification'))))
            else:
                self._ui.temporalProfileType.setCurrentIndex(
                    self._ui.temporalProfileType.findData(TemporalProfileType(TemporalProfileType.CONSTANT)))

            self._ui.constantValue.setText(db.getValue(self._xpath + '/constant'))
        else:
            self._ui.groupBox.setChecked(False)
            self._ui.specificationMethod.setCurrentIndex(
                self._ui.specificationMethod.findData(SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE))

        self._ui.temporalProfileType.setEnabled(GeneralDB.isTimeTransient())

        self._onSpecificationMethodChanged()
        self._onTemporalProfileTypeChanged()

    async def updateDB(self, newDB):
        db = coredb.CoreDB()
        if self._ui.groupBox.isChecked():
            newDB.setAttribute(self._xpath, 'disabled', 'false')
            newDB.setValue(self._xpath + '/unit', self._ui.specificationMethod.currentData().value, None)
            specification = self._ui.temporalProfileType.currentData()
            newDB.setValue(self._xpath + '/specification', specification.value, None)
            if specification == TemporalProfileType.CONSTANT:
                newDB.setValue(self._xpath + '/constant', self._ui.constantValue.text(), self._title)
            elif specification == TemporalProfileType.PIECEWISE_LINEAR:
                if self._piecewiseLinear is not None:
                    newDB.setValue(self._xpath + '/piecewiseLinear/t',
                                 self._piecewiseLinear[0], self.tr(f'{self._title} Piecewise Linear'))
                    newDB.setValue(self._xpath + '/piecewiseLinear/v',
                                 self._piecewiseLinear[1], self.tr(f'{self._title} Piecewise Linear'))
                elif not db.getValue(self._xpath + '/piecewiseLinear/t') == '':
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr(f'Edit {self._title} Piecewise Linear Values.'))
                    return False
            elif specification == TemporalProfileType.POLYNOMIAL:
                if self._polynomial is not None:
                    newDB.setValue(self._xpath + '/polynomial',
                                 self._polynomial, self.tr(f'{self._title} Polynomial'))
                elif not db.getValue(self._xpath + '/polynomial'):
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr(f'Edit {self._title} Polynomial Values.'))
                    return False
        else:
            newDB.setAttribute(self._xpath, 'disabled', 'true')

        return True

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

    def _edit(self):
        db = coredb.CoreDB()
        temporalProfileType = self._ui.temporalProfileType.currentData()
        if temporalProfileType == TemporalProfileType.PIECEWISE_LINEAR:
            if self._piecewiseLinear is None:
                self._piecewiseLinear = [
                    db.getValue(self._xpath + '/piecewiseLinear/t'),
                    db.getValue(self._xpath + '/piecewiseLinear/v')
                ]

            self._dialog = NumberInputDialog(self, self.tr("Piecewise Linear"),
                                             [self.tr("t"), self._title],
                                             [d.split() if d else [] for d in self._piecewiseLinear])
            self._dialog.accepted.connect(self._piecewiseLinearAccepted)
            self._dialog.open()
        elif temporalProfileType == TemporalProfileType.POLYNOMIAL:
            if self._polynomial is None:
                self._polynomial = db.getValue(self._xpath + '/polynomial')

            self._dialog = PolynomialDialog(self, self.tr("Polynomial"), self._polynomial.split())
            self._dialog.accepted.connect(self._polynomialAccepted)
            self._dialog.open()

    def _piecewiseLinearAccepted(self):
        self._piecewiseLinear = self._dialog.getValues()

    def _polynomialAccepted(self):
        self._polynomial = self._dialog.getValues()
