#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import JanafSpecificHeat
from .janaf_dialog_ui import Ui_JanafDialog


class JanafDialog(QDialog):
    def __init__(self, parent, title, xpath, data):
        super().__init__(parent)
        self._ui = Ui_JanafDialog()
        self._ui.setupUi(self)
        self.setWindowTitle(title)

        self._connectSignalsSlots()

        self._xpath = xpath + '/specificHeat/janaf'
        self._data = data

        self._load()

    def getValues(self):
        return self._data

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
            self._ui.tLow.validate(self.tr('T<sub>Low</sub>'), low=200)
            self._ui.tCommon.validate(self.tr('T<sub>Common</sub>>'))
            self._ui.tHigh.validate(self.tr('T<sub>High</sub>'), high=6000)

            self._ui.a0Low.validate(self.tr('Low Coefficient a0'))
            self._ui.a1Low.validate(self.tr('Low Coefficient a1'))
            self._ui.a2Low.validate(self.tr('Low Coefficient a2'))
            self._ui.a3Low.validate(self.tr('Low Coefficient a3'))
            self._ui.a4Low.validate(self.tr('Low Coefficient a4'))
            self._ui.a5Low.validate(self.tr('Low Coefficient a5'))
            # self._ui.a6Low.validate(self.tr('Low Coefficient a6'))

            self._ui.a0High.validate(self.tr('High Coefficient a0'))
            self._ui.a1High.validate(self.tr('High Coefficient a1'))
            self._ui.a2High.validate(self.tr('High Coefficient a2'))
            self._ui.a3High.validate(self.tr('High Coefficient a3'))
            self._ui.a4High.validate(self.tr('High Coefficient a4'))
            self._ui.a5High.validate(self.tr('High Coefficient a5'))
            self._ui.a6High.validate(self.tr('High Coefficient a6'))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        commonTemperature = self._ui.tCommon.validatedFloat()
        if self._ui.tLow.validatedFloat() >= commonTemperature:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('T<sub>Common</sub> must be greater than T<sub>Low</sub>.'))
            return

        if self._ui.tHigh.validatedFloat() <= commonTemperature:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('T<sub>Common</sub> must be less than T<sub>High</sub>.'))
            return

        self._data = JanafSpecificHeat(
            lowTemperature=self._ui.tLow.text(),
            commonTemperature=self._ui.tCommon.text(),
            highTemperature=self._ui.tHigh.text(),
            lowCoefficients=f"{self._ui.a0Low.text()} "
                            f"{self._ui.a1Low.text()} "
                            f"{self._ui.a2Low.text()} "
                            f"{self._ui.a3Low.text()} "
                            f"{self._ui.a4Low.text()} "
                            f"{self._ui.a5Low.text()} "
                            f"{self._ui.a6Low.text()}",
            highCoefficients=f"{self._ui.a0High.text()} "
                             f"{self._ui.a1High.text()} "
                             f"{self._ui.a2High.text()} "
                             f"{self._ui.a3High.text()} "
                             f"{self._ui.a4High.text()} "
                             f"{self._ui.a5High.text()} "
                             f"{self._ui.a6High.text()}"
        )

        self.accept()
