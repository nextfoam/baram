#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import NonNewtonianPowerLawViscosity
from .viscosity_non_newtonian_power_law_dialog_ui import Ui_ViscosityNonNewtonianPowerLaw


class ViscosityNonNewtonianPowerLawDialog(QDialog):
    def __init__(self, parent: QWidget, xpath: str, data: NonNewtonianPowerLawViscosity | None):
        super().__init__(parent)
        self._ui = Ui_ViscosityNonNewtonianPowerLaw()
        self._ui.setupUi(self)

        self._data: NonNewtonianPowerLawViscosity = data

        self._connectSignalsSlots()

        self._xpath = xpath + '/transport/nonNewtonianPowerLaw'
        self._load()

    def getValues(self):
        return self._data

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            self._data = NonNewtonianPowerLawViscosity(
                maximumViscosity=self._ui.maximumViscosity.pFloat(self.tr('Maximum Viscosity')),
                minimumViscosity=self._ui.minimumViscosity.pFloat(self.tr('Minimum Viscosity')),
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
            self._ui.maximumViscosity.setText(db.getValue(self._xpath + '/maximumViscosity'))
            self._ui.minimumViscosity.setText(db.getValue(self._xpath + '/minimumViscosity'))
            self._ui.consistencyIndex.setText(db.getValue(self._xpath + '/consistencyIndex'))
            self._ui.powerLawIndex.setText(db.getValue(self._xpath + '/powerLawIndex'))
        else:
            self._ui.maximumViscosity.setPFloat(self._data.maximumViscosity)
            self._ui.minimumViscosity.setPFloat(self._data.minimumViscosity)
            self._ui.consistencyIndex.setPFloat(self._data.consistencyIndex)
            self._ui.powerLawIndex.setPFloat(self._data.powerLawIndex)
