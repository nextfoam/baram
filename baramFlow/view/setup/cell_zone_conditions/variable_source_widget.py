#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import SpecificationMethod, TemporalProfileType
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.view.widgets.number_input_dialog import PiecewiseLinearDialog, PolynomialDialog
from .variable_source_widget_ui import Ui_VariableSourceWidget


class VariableSourceWidget(QWidget):
    def __init__(self, title, xpath):
        super().__init__()
        self._ui = Ui_VariableSourceWidget()
        self._ui.setupUi(self)

        self._specificationMethods = {
            SpecificationMethod.VALUE_PER_UNIT_VOLUME.value: self.tr("Value per Unit Volume"),
            SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE.value: self.tr("Value for Entire Cell Zone"),
        }

        self._temporalProfileTypes = {
            TemporalProfileType.CONSTANT.value: self.tr("Constant"),
            TemporalProfileType.PIECEWISE_LINEAR.value: self.tr("Piecewise Linear"),
            TemporalProfileType.POLYNOMIAL.value: self.tr("Polynomial"),
        }

        self._db = coredb.CoreDB()
        self._title = title
        self._xpath = xpath
        self._piecewiseLinear = None
        self._polynomial = None

        self._ui.groupBox.setTitle(title)
        self._setupCombo(self._ui.specificationMethod, self._specificationMethods)
        self._setupCombo(self._ui.temporalProfileType, self._temporalProfileTypes)

        self._connectSignalsSlots()

    def load(self):
        self._ui.groupBox.setChecked(self._db.getAttribute(self._xpath, 'disabled') == 'false')
        self._ui.specificationMethod.setCurrentText(
            self._specificationMethods[self._db.getValue(self._xpath + '/unit')])

        if GeneralDB.isTimeTransient():
            self._ui.temporalProfileType.setCurrentText(
                self._temporalProfileTypes[self._db.getValue(self._xpath + '/specification')]
            )
        else:
            self._ui.temporalProfileType.setCurrentText(
                self._temporalProfileTypes[TemporalProfileType.CONSTANT.value]
            )
            self._ui.temporalProfileType.setEnabled(False)

        self._ui.constantValue.setText(self._db.getValue(self._xpath + '/constant'))

    def appendToWriter(self, writer):
        if self._ui.groupBox.isChecked():
            writer.setAttribute(self._xpath, 'disabled', 'false')
            writer.append(self._xpath + '/unit', self._ui.specificationMethod.currentData(), None)
            specification = self._ui.temporalProfileType.currentData()
            writer.append(self._xpath + '/specification', specification, None)
            if specification == TemporalProfileType.CONSTANT.value:
                writer.append(self._xpath + '/constant', self._ui.constantValue.text(), self._title)
            elif specification == TemporalProfileType.PIECEWISE_LINEAR.value:
                if self._piecewiseLinear is not None:
                    writer.append(self._xpath + '/piecewiseLinear/t',
                                  self._piecewiseLinear[0], self.tr(f'{self._title} Piecewise Linear'))
                    writer.append(self._xpath + '/piecewiseLinear/v',
                                  self._piecewiseLinear[1], self.tr(f'{self._title} Piecewise Linear'))
                elif not self._db.getValue(self._xpath + '/piecewiseLinear/t') == '':
                    QMessageBox.critical(self, self.tr("Input Error"),
                                         self.tr(f'Edit {self._title} Piecewise Linear Values.'))
                    return False
            elif specification == TemporalProfileType.POLYNOMIAL.value:
                if self._polynomial is not None:
                    writer.append(self._xpath + '/polynomial',
                                  self._polynomial, self.tr(f'{self._title} Polynomial'))
                elif not self._db.getValue(self._xpath + '/polynomial'):
                    QMessageBox.critical(self, self.tr("Input Error"),
                                         self.tr(f'Edit {self._title} Polynomial Values.'))
                    return False
        else:
            writer.setAttribute(self._xpath, 'disabled', 'true')

        return True

    def _connectSignalsSlots(self):
        self._ui.groupBox.toggled.connect(self._toggled)
        self._ui.temporalProfileType.currentIndexChanged.connect(self._temporalProfileTypeChanged)
        self._ui.edit.clicked.connect(self._edit)

    def _setupCombo(self, combo, items):
        for value, text in items.items():
            combo.addItem(text, value)

    def _toggled(self, on):
        if on:
            self._temporalProfileTypeChanged()

    def _temporalProfileTypeChanged(self):
        temporalProfileType = self._ui.temporalProfileType.currentData()
        self._ui.edit.setEnabled(temporalProfileType != TemporalProfileType.CONSTANT.value)
        self._ui.constantValue.setEnabled(temporalProfileType == TemporalProfileType.CONSTANT.value)

    def _edit(self):
        temporalProfileType = self._ui.temporalProfileType.currentData()
        if temporalProfileType == TemporalProfileType.PIECEWISE_LINEAR.value:
            if self._ui.groupBox.title() == "Energy":
                if self._piecewiseLinear is None:
                    self._piecewiseLinear = [
                        self._db.getValue(self._xpath + '/piecewiseLinear/t'),
                        self._db.getValue(self._xpath + '/piecewiseLinear/v')
                    ]

                self._dialog = PiecewiseLinearDialog(self, self.tr("Piecewise Linear"),
                                                     [self.tr("t"), self.tr("Energy")], self._piecewiseLinear)
                self._dialog.accepted.connect(self._piecewiseLinearAccepted)
                self._dialog.open()
            else:
                if self._piecewiseLinear is None:
                    self._piecewiseLinear = [
                        self._db.getValue(self._xpath + '/piecewiseLinear/t'),
                        self._db.getValue(self._xpath + '/piecewiseLinear/v')
                    ]

                self._dialog = PiecewiseLinearDialog(self, self.tr("Piecewise Linear"),
                                                     [self.tr("t"), self.tr("Flow Rate")], self._piecewiseLinear)
                self._dialog.accepted.connect(self._piecewiseLinearAccepted)
                self._dialog.open()
        elif temporalProfileType == TemporalProfileType.POLYNOMIAL.value:
            if self._polynomial is None:
                self._polynomial = self._db.getValue(self._xpath + '/polynomial')

            self._dialog = PolynomialDialog(self, self.tr("Polynomial"), self._polynomial)
            self._dialog.accepted.connect(self._polynomialAccepted)
            self._dialog.open()

    def _piecewiseLinearAccepted(self):
        self._piecewiseLinear = self._dialog.getValues()

    def _polynomialAccepted(self):
        self._polynomial = self._dialog.getValues()
