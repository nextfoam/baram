#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import FlowRateInletSpecification, BoundaryDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from baramFlow.view.widgets.enum_combo_box import EnumComboBox
from .flow_rate_inlet_dialog_ui import Ui_FlowRateInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class FlowRateInletDialog(ResizableDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FlowRateInletDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        self._flowRateSpecificationMethodsCombo = EnumComboBox(self._ui.flowRateSpecificationMethod)

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

        self._setupSpecificationMethodCombo()

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        path = self._xpath + '/flowRateInlet'

        writer = CoreDBWriter()
        specification = self._ui.flowRateSpecificationMethod.currentData()
        writer.append(path + '/flowRate/specification', specification, None)
        if self._flowRateSpecificationMethodsCombo.isSelected(FlowRateInletSpecification.VOLUME_FLOW_RATE):
            writer.append(path + '/flowRate/volumeFlowRate', self._ui.volumeFlowRate.text(),
                          self.tr('Volume Flow Rate'))
        elif self._flowRateSpecificationMethodsCombo.isSelected(FlowRateInletSpecification.MASS_FLOW_RATE):
            writer.append(path + '/flowRate/massFlowRate', self._ui.massFlowRate.text(), self.tr('Mass Flow Rate'))

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

        errorCount = writer.write()
        if errorCount > 0:
            self._temperatureWidget.rollbackWriting()
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self._temperatureWidget.completeWriting()
            self.accept()

    def _connectSignalsSlots(self):
        self._flowRateSpecificationMethodsCombo.currentValueChanged.connect(self._flowRateSpecificationMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + '/flowRateInlet'

        self._flowRateSpecificationMethodsCombo.setCurrentValue(db.getValue(path + '/flowRate/specification'))
        self._ui.volumeFlowRate.setText(db.getValue(path + '/flowRate/volumeFlowRate'))
        self._ui.massFlowRate.setText(db.getValue(path + '/flowRate/massFlowRate'))
        self._flowRateSpecificationMethodChanged()

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
        self._volumeFractionWidget.load(self._xpath + '/volumeFractions')
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

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
