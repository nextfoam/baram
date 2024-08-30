#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

from baramFlow.coredb import coredb
from baramFlow.coredb.region_db import CavitationModel
from baramFlow.view.widgets.enum_button_group import EnumButtonGroup
from .cavitation_constants_widget import CavitationConstantsWidget


class CavitationWidget(QObject):
    def __init__(self, ui, xpath):
        super().__init__()
        self._ui = ui
        self._xpath = xpath + '/phaseInteractions/massTransfers/massTransfer[mechanism="cavitation"]/cavitation'

        self._modelRadios = EnumButtonGroup()
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

        model = CavitationModel(db.getValue(self._xpath + '/model'))
        if model == CavitationModel.NONE:
            self._ui.cavitation.setChecked(False)
            model = CavitationModel.SCHNERR_SAUER
        else:
            self._ui.cavitation.setChecked(True)

        self._modelRadios.setCheckedData(model)
        self._ui.vaporizationPressure.setText(db.getValue(self._xpath + '/vaporizationPressure'))

        self._modelConstants = {}
        layout = self._ui.cavitation.layout()
        for m in CavitationModel:
            if m != CavitationModel.NONE:
                self._modelConstants[m] = CavitationConstantsWidget(m, f'{self._xpath}/{m.value}')
                layout.addWidget(self._modelConstants[m])
                self._modelConstants[m].setVisible(m == model)
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

    def _modelChanged(self, model):
        for m, widget in self._modelConstants.items():
            widget.setVisible(m == model)
