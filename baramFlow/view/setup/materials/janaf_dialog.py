#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import JanafSpecificHeat
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
        if self._data is None:
            db = coredb.CoreDB()
            self._ui.tLow.setText(db.getValue(self._xpath + '/lowTemperature'))
            self._ui.tCommon.setText(db.getValue(self._xpath + '/commonTemperature'))
            self._ui.tHigh.setText(db.getValue(self._xpath + '/highTemperature'))
            lowCoefficients = db.getValue(self._xpath + '/lowCoefficients')
            highCoefficients = db.getValue(self._xpath + '/highCoefficients')

        else:
            self._ui.tLow.setText(self._data.lowTemperature)
            self._ui.tCommon.setText(self._data.commonTemperature)
            self._ui.tHigh.setText(self._data.highTemperature)
            lowCoefficients = self._data.lowCoefficients
            highCoefficients = self._data.highCoefficients

        coefficients = lowCoefficients.split()
        self._ui.a0Low.setText(coefficients[0])
        self._ui.a1Low.setText(coefficients[1])
        self._ui.a2Low.setText(coefficients[2])
        self._ui.a3Low.setText(coefficients[3])
        self._ui.a4Low.setText(coefficients[4])
        self._ui.a5Low.setText(coefficients[5])
        self._ui.a6Low.setText(coefficients[6])

        coefficients = highCoefficients.split()
        self._ui.a0High.setText(coefficients[0])
        self._ui.a1High.setText(coefficients[1])
        self._ui.a2High.setText(coefficients[2])
        self._ui.a3High.setText(coefficients[3])
        self._ui.a4High.setText(coefficients[4])
        self._ui.a5High.setText(coefficients[5])
        self._ui.a6High.setText(coefficients[6])

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            tLow    = self._ui.tLow.pFloat(self.tr('T<sub>Low</sub>'), low=200)
            tCommon = self._ui.tCommon.pFloat(self.tr('T<sub>Common</sub>>'))
            tHigh   = self._ui.tHigh.pFloat(self.tr('T<sub>High</sub>'), high=6000)

            a0Low = self._ui.a0Low.pFloat(self.tr('Low Coefficient a0'))
            a1Low = self._ui.a1Low.pFloat(self.tr('Low Coefficient a1'))
            a2Low = self._ui.a2Low.pFloat(self.tr('Low Coefficient a2'))
            a3Low = self._ui.a3Low.pFloat(self.tr('Low Coefficient a3'))
            a4Low = self._ui.a4Low.pFloat(self.tr('Low Coefficient a4'))
            a5Low = self._ui.a5Low.pFloat(self.tr('Low Coefficient a5'))
            a6Low = self._ui.a6Low.pFloat(self.tr('Low Coefficient a6'))

            a0High =self._ui.a0High.pFloat(self.tr('High Coefficient a0'))
            a1High =self._ui.a1High.pFloat(self.tr('High Coefficient a1'))
            a2High =self._ui.a2High.pFloat(self.tr('High Coefficient a2'))
            a3High =self._ui.a3High.pFloat(self.tr('High Coefficient a3'))
            a4High =self._ui.a4High.pFloat(self.tr('High Coefficient a4'))
            a5High =self._ui.a5High.pFloat(self.tr('High Coefficient a5'))
            a6High =self._ui.a6High.pFloat(self.tr('High Coefficient a6'))

            if tLow >= tCommon:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('T<sub>Common</sub> must be greater than T<sub>Low</sub>.'))
                return

            if tHigh <= tCommon:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('T<sub>Common</sub> must be less than T<sub>High</sub>.'))
                return

            self.dataAccepted.emit(
                JanafSpecificHeat(lowTemperature=str(tLow),
                                  commonTemperature=str(tCommon),
                                  highTemperature=str(tHigh),
                                  lowCoefficients=f"{str(a0Low)} "
                                                  f"{str(a1Low)} "
                                                  f"{str(a2Low)} "
                                                  f"{str(a3Low)} "
                                                  f"{str(a4Low)} "
                                                  f"{str(a5Low)} "
                                                  f"{str(a6Low)}",
                                  highCoefficients=f"{str(a0High)} "
                                                   f"{str(a1High)} "
                                                   f"{str(a2High)} "
                                                   f"{str(a3High)} "
                                                   f"{str(a4High)} "
                                                   f"{str(a5High)} "
                                                   f"{str(a6High)}"))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()
