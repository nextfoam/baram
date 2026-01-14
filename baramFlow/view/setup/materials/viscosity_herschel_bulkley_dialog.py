#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox
from widgets.validation.validation import FormValidator

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import HerschelBulkleyViscosity
from .viscosity_herschel_bulkley_dialog_ui import Ui_ViscosityHerschelBulkleyDialog


class ViscosityHerschelBulkleyDialog(QDialog):
    def __init__(self, parent, xpath, data):
        super().__init__(parent)
        self._ui = Ui_ViscosityHerschelBulkleyDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        self._xpath = xpath + '/transport/herschelBulkley'
        self._load(data)

    def getValues(self):
        return HerschelBulkleyViscosity(
            zeroShearViscosity=self._ui.zeroShearViscosity.text(),
            yieldStressThreshold=self._ui.yieldStressThreshold.text(),
            consistencyIndex=self._ui.consistencyIndex.text(),
            powerLawIndex=self._ui.powerLawIndex.text()
        )

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        validator = FormValidator()
        validator.addRequiredValidation(self._ui.zeroShearViscosity, self.tr('Zero Shear Viscosity'))
        validator.addRequiredValidation(self._ui.yieldStressThreshold, self.tr('Yield Stress Threshold'))
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
            self._ui.zeroShearViscosity.setText(db.getValue(self._xpath + '/zeroShearViscosity'))
            self._ui.yieldStressThreshold.setText(db.getValue(self._xpath + '/yieldStressThreshold'))
            self._ui.consistencyIndex.setText(db.getValue(self._xpath + '/consistencyIndex'))
            self._ui.powerLawIndex.setText(db.getValue(self._xpath + '/powerLawIndex'))
        else:
            self._ui.zeroShearViscosity.setText(data.zeroShearViscosity)
            self._ui.yieldStressThreshold.setText(data.yieldStressThreshold)
            self._ui.consistencyIndex.setText(data.consistencyIndex)
            self._ui.powerLawIndex.setText(data.powerLawIndex)
