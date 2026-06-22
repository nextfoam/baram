#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.boundary.boundary_patch import FlowRateInletUpdate
from baramFlow.base.boundary.flow_rate_port import FlowRateSpecification, BoundaryFlowRate
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .conditional_widget_helper import ConditionalWidgetHelper
from .flow_rate_inlet_dialog_ui import Ui_FlowRateInletDialog


class FlowRateInletDialog(ResizableDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FlowRateInletDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = None
        self._temperatureWidget = None
        self._volumeFractionWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._volumeFractionWidget = ConditionalWidgetHelper.volumeFractionWidget(rname, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        if not GeneralDB.isCompressible():
            self._ui.flowRateSpecificationMethod.addItem(self.tr('Volume Flow Rate'),
                                                         FlowRateSpecification.VOLUME_FLOW_RATE)
        self._ui.flowRateSpecificationMethod.addItem(self.tr('Mass Flow Rate'), FlowRateSpecification.MASS_FLOW_RATE)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        #
        # Validation check for parameters
        #
        valid, msg = self._volumeFractionWidget.validate()
        if not valid:
            await AsyncMessageBox().warning(self, self.tr('Warning'), msg)
            return
        # ToDo: Add validation for other parameters

        try:
            specification = self._ui.flowRateSpecificationMethod.currentData()
            flowRate = BoundaryFlowRate(specification=specification)
            if specification == FlowRateSpecification.VOLUME_FLOW_RATE:
                flowRate.volumeFlowRate = self._ui.volumeFlowRate.pFloat(self.tr('Volume Flow Rate'))
            elif specification == FlowRateSpecification.MASS_FLOW_RATE:
                flowRate.massFlowRate = self._ui.massFlowRate.pFloat(self.tr('Mass Flow Rate'))

            writer = CoreDBWriter()

            if not self._turbulenceWidget.appendToWriter(writer):
                return

            if not self._temperatureWidget.appendToWriter(writer):
                return

            if not await self._volumeFractionWidget.appendToWriter(writer, self._xpath + '/volumeFractions'):
                return

            if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
                return

            if not await self._speciesWidget.appendToWriter(writer, self._xpath + '/species'):
                return

            data = FlowRateInletUpdate(flowRate=flowRate,
                                       turbulence=self._turbulenceWidget.data())

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _connectSignalsSlots(self):
        self._ui.flowRateSpecificationMethod.currentIndexChanged.connect(self._onFlowRateSpecificationMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + '/flowRateInlet'

        self._ui.flowRateSpecificationMethod.setCurrentIndex(
            self._ui.flowRateSpecificationMethod.findData(
                FlowRateSpecification(db.getValue(path + '/flowRate/specification'))))
        self._ui.volumeFlowRate.setText(db.getValue(path + '/flowRate/volumeFlowRate'))
        self._ui.massFlowRate.setText(db.getValue(path + '/flowRate/massFlowRate'))
        self._onFlowRateSpecificationMethodChanged()

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
        self._volumeFractionWidget.load(self._xpath + '/volumeFractions')
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _onFlowRateSpecificationMethodChanged(self):
        specification = self._ui.flowRateSpecificationMethod.currentData()
        self._ui.volumeFlowRateWidget.setVisible(specification == FlowRateSpecification.VOLUME_FLOW_RATE)
        self._ui.massFlowRateWidget.setVisible(specification == FlowRateSpecification.MASS_FLOW_RATE)
