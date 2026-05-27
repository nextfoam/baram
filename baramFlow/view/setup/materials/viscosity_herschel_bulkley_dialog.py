#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import HerschelBulkleyViscosity
from .viscosity_herschel_bulkley_dialog_ui import Ui_ViscosityHerschelBulkleyDialog


class ViscosityHerschelBulkleyDialog(QDialog):
    def __init__(self, parent: QWidget, xpath: str, data: HerschelBulkleyViscosity | None):
        super().__init__(parent)
        self._ui = Ui_ViscosityHerschelBulkleyDialog()
        self._ui.setupUi(self)

        self._data: HerschelBulkleyViscosity = data

        self._connectSignalsSlots()

        self._xpath = xpath + '/transport/herschelBulkley'
        self._load()

    def getValues(self):
        return self._data

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            self._data = HerschelBulkleyViscosity(
                zeroShearViscosity=self._ui.zeroShearViscosity.pFloat(self.tr('Zero Shear Viscosity')),
                yieldStressThreshold=self._ui.yieldStressThreshold.pFloat(self.tr('Yield Stress Threshold')),
                consistencyIndex=self._ui.consistencyIndex.pFloat(self.tr('Consistency Index')),
                powerLawIndex=self._ui.powerLawIndex.pFloat(self.tr('Power Law Index'))
            )
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _load(self):
        if self._data is None:
            db = coredb.CoreDB()
            self._ui.zeroShearViscosity.setText(db.getValue(self._xpath + '/zeroShearViscosity'))
            self._ui.yieldStressThreshold.setText(db.getValue(self._xpath + '/yieldStressThreshold'))
            self._ui.consistencyIndex.setText(db.getValue(self._xpath + '/consistencyIndex'))
            self._ui.powerLawIndex.setText(db.getValue(self._xpath + '/powerLawIndex'))
        else:
            self._ui.zeroShearViscosity.setPFloat(self._data.zeroShearViscosity)
            self._ui.yieldStressThreshold.setPFloat(self._data.yieldStressThreshold)
            self._ui.consistencyIndex.setPFloat(self._data.consistencyIndex)
            self._ui.powerLawIndex.setPFloat(self._data.powerLawIndex)
