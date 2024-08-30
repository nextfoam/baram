#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.region_db import CavitationModel
from .cavitation_constants_widget_ui import Ui_CavitationConstantsWidget


MODEL_CONSTANTS = {
    'bubbleDiameter': [CavitationModel.SCHNERR_SAUER, CavitationModel.ZWART_GERBER_BELAMRI],
    'bubbleNumberDensity': [CavitationModel.SCHNERR_SAUER],
    'nucleationSiteVolumeFraction': [CavitationModel.ZWART_GERBER_BELAMRI],
    'meanFlowTimeScale': [CavitationModel.KUNZ, CavitationModel.MERKLE],
    'freeStreamVelocity': [CavitationModel.KUNZ, CavitationModel.MERKLE]
}


class CavitationConstantsWidget(QWidget):
    def __init__(self, model, xpath):
        super().__init__()
        self._ui = Ui_CavitationConstantsWidget()
        self._ui.setupUi(self)

        self._model = model
        self._xpath = xpath + '/'
        self._constants = None

    def load(self):
        self._constants = []
        self._ui.evaporationCoefficient.setText(coredb.CoreDB().getValue(self._xpath + 'evaporationCoefficient'))
        self._ui.condensationCoefficient.setText(coredb.CoreDB().getValue(self._xpath + 'condensationCoefficient'))
        self._loadConstant(self._ui.bubbleDiameter, 'bubbleDiameter', self.tr('Bubble Diameter'))
        self._loadConstant(self._ui.bubbleNumberDensity, 'bubbleNumberDensity', self.tr('Bubble Number Density'))
        self._loadConstant(self._ui.nucleationSiteVolumeFraction, 'nucleationSiteVolumeFraction',
                           self.tr('Nucleation Site Volume Fraction'))
        self._loadConstant(self._ui.meanFlowTimeScale, 'meanFlowTimeScale', self.tr('Mean Flow Time Scale'))
        self._loadConstant(self._ui.freeStreamVelocity, 'freeStreamVelocity', self.tr('Free Stream Velocity'))

    def save(self, db):
        db.setValue(self._xpath + 'evaporationCoefficient', self._ui.evaporationCoefficient.text(),
                    self.tr('Evaporation Coefficient'))
        db.setValue(self._xpath + 'condensationCoefficient', self._ui.condensationCoefficient.text(),
                    self.tr('Condensation Coefficient'))
        for edit, xpath, name in self._constants:
            db.setValue(xpath, edit.text(), name)

    def _loadConstant(self, edit, constant, name):
        if self._model in MODEL_CONSTANTS[constant]:
            xpath = self._xpath + constant
            self._ui.constantsLayout.setRowVisible(edit, True)
            edit.setText(coredb.CoreDB().getValue(xpath))
            self._constants.append((edit, xpath, name))
        else:
            self._ui.constantsLayout.setRowVisible(edit, False)
