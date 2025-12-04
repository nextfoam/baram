#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox
from widgets.validation.validation import FormValidator

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import NonNewtonianPowerLawViscosity
from .viscosity_non_newtonian_power_law_dialog_ui import Ui_ViscosityNonNewtonianPowerLaw


class ViscosityNonNewtonianPowerLawDialog(QDialog):
    def __init__(self, parent, xpath, data):
        super().__init__(parent)
        self._ui = Ui_ViscosityNonNewtonianPowerLaw()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        self._xpath = xpath + '/transport/nonNewtonianPowerLaw'
        self._load(data)

    def getValues(self):
        return NonNewtonianPowerLawViscosity(
            maximumViscosity=self._ui.maximumViscosity.text(),
            minimumViscosity=self._ui.minimumViscosity.text(),
            consistencyIndex=self._ui.consistencyIndex.text(),
            powerLawIndex=self._ui.powerLawIndex.text()
        )

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        validator = FormValidator()
        validator.addRequiredValidation(self._ui.maximumViscosity, self.tr('Maximum Viscosity'))
        validator.addRequiredValidation(self._ui.minimumViscosity, self.tr('Minimum Viscosity'))
        validator.addRequiredValidation(self._ui.consistencyIndex, self.tr('Consistency Index'))
        validator.addRequiredValidation(self._ui.powerLawIndex, self.tr('Power Law Index'))

        valid, msg = validator.validate()
        if valid:
            self.accept()
        else:
            await AsyncMessageBox().information(self, self.tr('Input Error'), msg)

    def _load(self, data):
        if data is None:
            db = coredb.CoreDB()
            self._ui.maximumViscosity.setText(db.getValue(self._xpath + '/maximumViscosity'))
            self._ui.minimumViscosity.setText(db.getValue(self._xpath + '/minimumViscosity'))
            self._ui.consistencyIndex.setText(db.getValue(self._xpath + '/consistencyIndex'))
            self._ui.powerLawIndex.setText(db.getValue(self._xpath + '/powerLawIndex'))
        else:
            self._ui.maximumViscosity.setText(data.maximumViscosity)
            self._ui.minimumViscosity.setText(data.minimumViscosity)
            self._ui.consistencyIndex.setText(data.consistencyIndex)
            self._ui.powerLawIndex.setText(data.powerLawIndex)
