#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.boundary.boundary_patch import FlowRateOutletUpdate
from baramFlow.base.boundary.flow_rate_port import FlowRateSpecification, BoundaryFlowRate
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .flow_rate_outlet_dialog_ui import Ui_FlowRateOutletDialog


class FlowRateOutletDialog(ResizableDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FlowRateOutletDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._xpath = BoundaryDB.getXPath(bcid)

        if not GeneralDB.isCompressible():
            self._ui.flowRateSpecificationMethod.addItem(self.tr('Volume Flow Rate'),
                                                         FlowRateSpecification.VOLUME_FLOW_RATE)
        self._ui.flowRateSpecificationMethod.addItem(self.tr('Mass Flow Rate'), FlowRateSpecification.MASS_FLOW_RATE)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            specification = self._ui.flowRateSpecificationMethod.currentData()
            flowRate = BoundaryFlowRate(specification=specification)
            if specification == FlowRateSpecification.VOLUME_FLOW_RATE:
                flowRate.volumeFlowRate = str(PFloat(self._ui.volumeFlowRate.text(), self.tr('Volume Flow Rate')))
            elif specification == FlowRateSpecification.MASS_FLOW_RATE:
                flowRate.massFlowRate = str(PFloat(self._ui.massFlowRate.text(), self.tr('Mass Flow Rate')))

            data = FlowRateOutletUpdate(flowRate=flowRate)

            BoundaryService.updateBoundaryCondition(self._bcid, data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _connectSignalsSlots(self):
        self._ui.flowRateSpecificationMethod.currentIndexChanged.connect(self._onFlowRateSpecificationMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + '/flowRateOutlet'

        self._ui.flowRateSpecificationMethod.setCurrentIndex(
            self._ui.flowRateSpecificationMethod.findData(
                FlowRateSpecification(db.getValue(path + '/flowRate/specification'))))
        self._ui.volumeFlowRate.setText(db.getValue(path + '/flowRate/volumeFlowRate'))
        self._ui.massFlowRate.setText(db.getValue(path + '/flowRate/massFlowRate'))
        self._onFlowRateSpecificationMethodChanged()

    def _onFlowRateSpecificationMethodChanged(self):
        specification = self._ui.flowRateSpecificationMethod.currentData()
        self._ui.volumeFlowRateWidget.setVisible(specification == FlowRateSpecification.VOLUME_FLOW_RATE)
        self._ui.massFlowRateWidget.setVisible(specification == FlowRateSpecification.MASS_FLOW_RATE)
