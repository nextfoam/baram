#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import QObject

from baramFlow.coredb import coredb
from baramFlow.coredb.region_db import CavitationModel
from baramFlow.view.widgets.enum_button_group import EnumButtonGroup
from widgets.async_message_box import AsyncMessageBox
from .cavitation_constants_widget import CavitationConstantsWidget


class CavitationWidget(QObject):
    def __init__(self, parent, ui, xpath):
        super().__init__()
        self._parent = parent
        self._ui = ui
        self._xpath = xpath + '/phaseInteractions/massTransfers/massTransfer[mechanism="cavitation"]/cavitation'

        self._modelRadios = EnumButtonGroup()

        self._model = None
        self._modelConstants = {}

        self._modelRadios.addEnumButton(self._ui.schnerrSauer, CavitationModel.SCHNERR_SAUER)
        self._modelRadios.addEnumButton(self._ui.kunz, CavitationModel.KUNZ)
        self._modelRadios.addEnumButton(self._ui.merkle, CavitationModel.MERKLE)
        self._modelRadios.addEnumButton(self._ui.zwartGerberBelamri, CavitationModel.ZWART_GERBER_BELAMRI)

        self._connectSignalsSlots()

    def setEnabled(self, enabled):
        if enabled:
            self._ui.cavitation.setEnabled(True)
        else:
            self._ui.cavitation.setEnabled(False)
            self._ui.cavitation.setChecked(False)

    def isChecked(self):
        return self._ui.cavitation.isChecked()

    def load(self):
        db = coredb.CoreDB()

        self._model = CavitationModel(db.getValue(self._xpath + '/model'))
        if self._model == CavitationModel.NONE:
            self._ui.cavitation.setChecked(False)
            self._model = CavitationModel.SCHNERR_SAUER
        else:
            self._ui.cavitation.setChecked(True)

        self._modelRadios.setCheckedData(self._model)
        self._ui.vaporizationPressure.setText(db.getValue(self._xpath + '/vaporizationPressure'))

        self._modelConstants = {}
        layout = self._ui.cavitation.layout()
        for m in CavitationModel:
            if m != CavitationModel.NONE:
                self._modelConstants[m] = CavitationConstantsWidget(m, f'{self._xpath}/{m.value}')
                layout.addWidget(self._modelConstants[m])
                self._modelConstants[m].setVisible(m == self._model)
                self._modelConstants[m].load()

    def updateDB(self, db):
        if not self._ui.cavitation.isChecked():
            db.setValue(self._xpath + '/model', CavitationModel.NONE.value)
            return True

        model = self._modelRadios.checkedData()
        db.setValue(self._xpath + '/model', model.value)
        db.setValue(self._xpath + '/vaporizationPressure', self._ui.vaporizationPressure.text(),
                    self.tr('Vaporization Pressure'))
        self._modelConstants[model].save(db)

    def _connectSignalsSlots(self):
        self._modelRadios.dataChecked.connect(self._modelChanged)

    @qasync.asyncSlot()
    async def _modelChanged(self, model):
        if model == CavitationModel.ZWART_GERBER_BELAMRI:
            self._modelRadios.setCheckedData(self._model)
            await AsyncMessageBox().information(
                self._parent, self.tr('Notification'),
                self.tr('Zwart-Gerber-Belamri model will be supported in next release.'))
            return

        self._model = model
        for m, widget in self._modelConstants.items():
            widget.setVisible(m == self._model)
