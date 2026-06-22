#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.base import NumberList
from baramFlow.base.material.specific_heat import JanafSpecificHeat
from .janaf_dialog_ui import Ui_JanafDialog


class JanafDialog(QDialog):
    dataAccepted = Signal(JanafSpecificHeat)

    def __init__(self, parent: QWidget, title: str, xpath: str, data: JanafSpecificHeat):
        super().__init__(parent)
        self._ui = Ui_JanafDialog()
        self._ui.setupUi(self)
        self.setWindowTitle(title)

        self._connectSignalsSlots()

        self._xpath: str = xpath + '/specificHeat/janaf'
        self._data: JanafSpecificHeat = data

        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        self._ui.tLow.setPFloat(self._data.lowTemperature)
        self._ui.tCommon.setPFloat(self._data.commonTemperature)
        self._ui.tHigh.setPFloat(self._data.highTemperature)

        self._ui.a0Low.setText(self._data.lowCoefficients.values[0])
        self._ui.a1Low.setText(self._data.lowCoefficients.values[1])
        self._ui.a2Low.setText(self._data.lowCoefficients.values[2])
        self._ui.a3Low.setText(self._data.lowCoefficients.values[3])
        self._ui.a4Low.setText(self._data.lowCoefficients.values[4])
        self._ui.a5Low.setText(self._data.lowCoefficients.values[5])
        self._ui.a6Low.setText(self._data.lowCoefficients.values[6])

        self._ui.a0High.setText(self._data.highCoefficients.values[0])
        self._ui.a1High.setText(self._data.highCoefficients.values[1])
        self._ui.a2High.setText(self._data.highCoefficients.values[2])
        self._ui.a3High.setText(self._data.highCoefficients.values[3])
        self._ui.a4High.setText(self._data.highCoefficients.values[4])
        self._ui.a5High.setText(self._data.highCoefficients.values[5])
        self._ui.a6High.setText(self._data.highCoefficients.values[6])

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            tLow    = self._ui.tLow.pFloat(self.tr('T<sub>Low</sub>'), low=200)
            tCommon = self._ui.tCommon.pFloat(self.tr('T<sub>Common</sub>>'))
            tHigh   = self._ui.tHigh.pFloat(self.tr('T<sub>High</sub>'), high=6000)

            if tLow >= tCommon:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('T<sub>Common</sub> must be greater than T<sub>Low</sub>.'))
                return

            if tHigh <= tCommon:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('T<sub>Common</sub> must be less than T<sub>High</sub>.'))
                return

            self.dataAccepted.emit(
                JanafSpecificHeat(
                    lowTemperature=tLow,
                    commonTemperature=tCommon,
                    highTemperature=tHigh,
                    lowCoefficients=NumberList(values=[self._ui.a0Low.value(self.tr('Low Coefficient a0')),
                                                       self._ui.a1Low.value(self.tr('Low Coefficient a1')),
                                                       self._ui.a2Low.value(self.tr('Low Coefficient a2')),
                                                       self._ui.a3Low.value(self.tr('Low Coefficient a3')),
                                                       self._ui.a4Low.value(self.tr('Low Coefficient a4')),
                                                       self._ui.a5Low.value(self.tr('Low Coefficient a5')),
                                                       self._ui.a6Low.value(self.tr('Low Coefficient a6'))]),
                    highCoefficients=NumberList(values=[self._ui.a0High.value(self.tr('High Coefficient a0')),
                                                        self._ui.a1High.value(self.tr('High Coefficient a1')),
                                                        self._ui.a2High.value(self.tr('High Coefficient a2')),
                                                        self._ui.a3High.value(self.tr('High Coefficient a3')),
                                                        self._ui.a4High.value(self.tr('High Coefficient a4')),
                                                        self._ui.a5High.value(self.tr('High Coefficient a5')),
                                                        self._ui.a6High.value(self.tr('High Coefficient a6'))])))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()
