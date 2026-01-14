#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox
from widgets.validation.validation import FormValidator

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import CrossViscosity
from .viscosity_cross_dialog_ui import Ui_ViscosityCrossDialog


class ViscosityCrossDialog(QDialog):
    def __init__(self, parent, xpath, data):
        super().__init__(parent)
        self._ui = Ui_ViscosityCrossDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        self._xpath = xpath + '/transport/cross'
        self._load(data)

    def getValues(self):
        return CrossViscosity(
            zeroShearViscosity=self._ui.zeroShearViscosity.text(),
            infiniteShearViscosity=self._ui.infiniteShearViscosity.text(),
            naturalTime=self._ui.naturalTime.text(),
            powerLawIndex=self._ui.powerLawIndex.text()
        )

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        validator = FormValidator()
        validator.addRequiredValidation(self._ui.zeroShearViscosity, self.tr('Zero Shear Viscosity'))
        validator.addRequiredValidation(self._ui.infiniteShearViscosity, self.tr('Infinite Shear Viscosity'))
        validator.addRequiredValidation(self._ui.naturalTime, self.tr('Natural Time'))
        validator.addRequiredValidation(self._ui.powerLawIndex, self.tr('Power Law Index'))

        valid, msg = validator.validate()
        if valid:
            self.accept()
        else:
            await AsyncMessageBox().information(self, self.tr('Input Error'), msg)

    def _load(self, data):
        if data is None:
            db = coredb.CoreDB()
            self._ui.zeroShearViscosity.setText(db.getValue(self._xpath + '/zeroShearViscosity'))
            self._ui.infiniteShearViscosity.setText(db.getValue(self._xpath + '/infiniteShearViscosity'))
            self._ui.naturalTime.setText(db.getValue(self._xpath + '/naturalTime'))
            self._ui.powerLawIndex.setText(db.getValue(self._xpath + '/powerLawIndex'))
        else:
            self._ui.zeroShearViscosity.setText(data.zeroShearViscosity)
            self._ui.infiniteShearViscosity.setText(data.infiniteShearViscosity)
            self._ui.naturalTime.setText(data.naturalTime)
            self._ui.powerLawIndex.setText(data.powerLawIndex)
