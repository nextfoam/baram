#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.material.transport import HerschelBulkleyViscosity
from .viscosity_herschel_bulkley_dialog_ui import Ui_ViscosityHerschelBulkleyDialog


class ViscosityHerschelBulkleyDialog(QDialog):
    dataAccepted = Signal(HerschelBulkleyViscosity)

    def __init__(self, parent: QWidget, data: HerschelBulkleyViscosity | None):
        super().__init__(parent)
        self._ui = Ui_ViscosityHerschelBulkleyDialog()
        self._ui.setupUi(self)

        self._data: HerschelBulkleyViscosity = data or HerschelBulkleyViscosity()

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            self.dataAccepted.emit(
                HerschelBulkleyViscosity(
                    zeroShearViscosity=self._ui.zeroShearViscosity.pFloat(self.tr('Zero Shear Viscosity')),
                    yieldStressThreshold=self._ui.yieldStressThreshold.pFloat(self.tr('Yield Stress Threshold')),
                    consistencyIndex=self._ui.consistencyIndex.pFloat(self.tr('Consistency Index')),
                    powerLawIndex=self._ui.powerLawIndex.pFloat(self.tr('Power Law Index'))))

            self.accept()
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

    def _load(self):
        self._ui.zeroShearViscosity.setPFloat(self._data.zeroShearViscosity)
        self._ui.yieldStressThreshold.setPFloat(self._data.yieldStressThreshold)
        self._ui.consistencyIndex.setPFloat(self._data.consistencyIndex)
        self._ui.powerLawIndex.setPFloat(self._data.powerLawIndex)
