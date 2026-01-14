#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox
from widgets.validation.validation import FormValidator

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import CarreauViscosity
from .viscosity_carreau_dialog_ui import Ui_ViscosityCarreauDialog


class ViscosityCarreauDialog(QDialog):
    def __init__(self, parent, xpath, data):
        super().__init__(parent)
        self._ui = Ui_ViscosityCarreauDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        self._xpath = xpath + '/transport/carreau'
        self._load(data)

    def getValues(self):
        return CarreauViscosity(
            zeroShearViscosity=self._ui.zeroShearViscosity.text(),
            infiniteShearViscosity=self._ui.infiniteShearViscosity.text(),
            relaxationTime=self._ui.relaxationTime.text(),
            powerLawIndex=self._ui.powerLawIndex.text(),
            linearityDeviation=self._ui.linearityDeviation.text()
        )

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        validator = FormValidator()
        validator.addRequiredValidation(self._ui.zeroShearViscosity, self.tr('Zero Shear Viscosity'))
        validator.addRequiredValidation(self._ui.infiniteShearViscosity, self.tr('Infinite Shear Viscosity'))
        validator.addRequiredValidation(self._ui.relaxationTime, self.tr('Relaxation Time'))
        validator.addRequiredValidation(self._ui.powerLawIndex, self.tr('Power Law Index'))
        validator.addRequiredValidation(self._ui.linearityDeviation, self.tr('Linearity Deviation'))

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
            self._ui.relaxationTime.setText(db.getValue(self._xpath + '/relaxationTime'))
            self._ui.powerLawIndex.setText(db.getValue(self._xpath + '/powerLawIndex'))
            self._ui.linearityDeviation.setText(db.getValue(self._xpath + '/linearityDeviation'))
        else:
            self._ui.zeroShearViscosity.setText(data.zeroShearViscosity)
            self._ui.infiniteShearViscosity.setText(data.infiniteShearViscosity)
            self._ui.relaxationTime.setText(data.relaxationTime)
            self._ui.powerLawIndex.setText(data.powerLawIndex)
            self._ui.linearityDeviation.setText(data.linearityDeviation)
