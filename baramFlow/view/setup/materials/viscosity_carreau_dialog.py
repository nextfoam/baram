#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.material.transport import CarreauViscosity
from .viscosity_carreau_dialog_ui import Ui_ViscosityCarreauDialog


class ViscosityCarreauDialog(QDialog):
    dataAccepted = Signal(CarreauViscosity)

    def __init__(self, parent: QWidget, data: CarreauViscosity | None):
        super().__init__(parent)
        self._ui = Ui_ViscosityCarreauDialog()
        self._ui.setupUi(self)

        self._data: CarreauViscosity = data or CarreauViscosity()

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            self.dataAccepted.emit(
                CarreauViscosity(
                    zeroShearViscosity=self._ui.zeroShearViscosity.pFloat(self.tr('Zero Shear Viscosity')),
                    infiniteShearViscosity=self._ui.infiniteShearViscosity.pFloat(self.tr('Infinite Shear Viscosity')),
                    relaxationTime=self._ui.relaxationTime.pFloat(self.tr('Relaxation Time')),
                    powerLawIndex=self._ui.powerLawIndex.pFloat(self.tr('Power Law Index')),
                    linearityDeviation=self._ui.linearityDeviation.pFloat(self.tr('Linearity Deviation'))))

            self.accept()
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

    def _load(self):
        self._ui.zeroShearViscosity.setPFloat(self._data.zeroShearViscosity)
        self._ui.infiniteShearViscosity.setPFloat(self._data.infiniteShearViscosity)
        self._ui.relaxationTime.setPFloat(self._data.relaxationTime)
        self._ui.powerLawIndex.setPFloat(self._data.powerLawIndex)
        self._ui.linearityDeviation.setPFloat(self._data.linearityDeviation)
