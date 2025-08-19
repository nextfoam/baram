#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import FlowRateInletSpecification, BoundaryDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from baramFlow.view.widgets.enum_combo_box import EnumComboBox
from .flow_rate_outlet_dialog_ui import Ui_FlowRateOutletDialog


class FlowRateOutletDialog(ResizableDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FlowRateOutletDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        self._flowRateSpecificationMethodsCombo = EnumComboBox(self._ui.flowRateSpecificationMethod)

        self._setupSpecificationMethodCombo()

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        path = self._xpath + '/flowRateOutlet'

        try:
            with coredb.CoreDB() as db:
                specification = self._ui.flowRateSpecificationMethod.currentData()
                db.setValue(path + '/flowRate/specification', specification)
                if self._flowRateSpecificationMethodsCombo.isSelected(FlowRateInletSpecification.VOLUME_FLOW_RATE):
                    db.setValue(path + '/flowRate/volumeFlowRate', self._ui.volumeFlowRate.text(),
                                self.tr('Volume Flow Rate'))
                elif self._flowRateSpecificationMethodsCombo.isSelected(FlowRateInletSpecification.MASS_FLOW_RATE):
                    db.setValue(path + '/flowRate/massFlowRate', self._ui.massFlowRate.text(),
                                self.tr('Mass Flow Rate'))
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

        self.accept()

    def _connectSignalsSlots(self):
        self._flowRateSpecificationMethodsCombo.currentValueChanged.connect(self._flowRateSpecificationMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + '/flowRateOutlet'

        self._flowRateSpecificationMethodsCombo.setCurrentValue(db.getValue(path + '/flowRate/specification'))
        self._ui.volumeFlowRate.setText(db.getValue(path + '/flowRate/volumeFlowRate'))
        self._ui.massFlowRate.setText(db.getValue(path + '/flowRate/massFlowRate'))
        self._flowRateSpecificationMethodChanged()

    def _setupSpecificationMethodCombo(self):
        if not GeneralDB.isCompressible():
            self._flowRateSpecificationMethodsCombo.addItem(FlowRateInletSpecification.VOLUME_FLOW_RATE,
                                                            self.tr('Volume Flow Rate'))
        self._flowRateSpecificationMethodsCombo.addItem(FlowRateInletSpecification.MASS_FLOW_RATE,
                                                        self.tr('Mass Flow Rate'))

    def _flowRateSpecificationMethodChanged(self):
        self._ui.volumeFlowRateWidget.setVisible(
            self._flowRateSpecificationMethodsCombo.isSelected(FlowRateInletSpecification.VOLUME_FLOW_RATE)
        )
        self._ui.massFlowRateWidget.setVisible(
            self._flowRateSpecificationMethodsCombo.isSelected(FlowRateInletSpecification.MASS_FLOW_RATE)
        )
