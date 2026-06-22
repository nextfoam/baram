#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.material.transport import CrossViscosity
from .viscosity_cross_dialog_ui import Ui_ViscosityCrossDialog


class ViscosityCrossDialog(QDialog):
    dataAccepted = Signal(CrossViscosity)

    def __init__(self, parent: QWidget, data: CrossViscosity | None):
        super().__init__(parent)
        self._ui = Ui_ViscosityCrossDialog()
        self._ui.setupUi(self)

        self._data: CrossViscosity = data or CrossViscosity()

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            self.dataAccepted.emit(
                CrossViscosity(
                    zeroShearViscosity=self._ui.zeroShearViscosity.pFloat(self.tr('Zero Shear Viscosity')),
                    infiniteShearViscosity=self._ui.infiniteShearViscosity.pFloat(self.tr('Infinite Shear Viscosity')),
                    naturalTime=self._ui.naturalTime.pFloat(self.tr('Natural Time')),
                    powerLawIndex=self._ui.powerLawIndex.pFloat(self.tr('Power Law Index'))))

            self.accept()
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

    def _load(self):
        self._ui.zeroShearViscosity.setPFloat(self._data.zeroShearViscosity)
        self._ui.infiniteShearViscosity.setPFloat(self._data.infiniteShearViscosity)
        self._ui.naturalTime.setPFloat(self._data.naturalTime)
        self._ui.powerLawIndex.setPFloat(self._data.powerLawIndex)
