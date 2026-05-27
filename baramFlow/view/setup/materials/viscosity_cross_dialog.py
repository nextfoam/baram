#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_schema import CrossViscosity
from .viscosity_cross_dialog_ui import Ui_ViscosityCrossDialog


class ViscosityCrossDialog(QDialog):
    def __init__(self, parent: QWidget, xpath: str, data: CrossViscosity | None):
        super().__init__(parent)
        self._ui = Ui_ViscosityCrossDialog()
        self._ui.setupUi(self)

        self._data: CrossViscosity = data

        self._connectSignalsSlots()

        self._xpath = xpath + '/transport/cross'
        self._load()

    def getValues(self):
        return self._data

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            self._data = CrossViscosity(
                zeroShearViscosity=self._ui.zeroShearViscosity.pFloat(self.tr('Zero Shear Viscosity')),
                infiniteShearViscosity=self._ui.infiniteShearViscosity.pFloat(self.tr('Infinite Shear Viscosity')),
                naturalTime=self._ui.naturalTime.pFloat(self.tr('Natural Time')),
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
            self._ui.infiniteShearViscosity.setText(db.getValue(self._xpath + '/infiniteShearViscosity'))
            self._ui.naturalTime.setText(db.getValue(self._xpath + '/naturalTime'))
            self._ui.powerLawIndex.setText(db.getValue(self._xpath + '/powerLawIndex'))
        else:
            self._ui.zeroShearViscosity.setPFloat(self._data.zeroShearViscosity)
            self._ui.infiniteShearViscosity.setPFloat(self._data.infiniteShearViscosity)
            self._ui.naturalTime.setPFloat(self._data.naturalTime)
            self._ui.powerLawIndex.setPFloat(self._data.powerLawIndex)
