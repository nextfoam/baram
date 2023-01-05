#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.models_db import ModelsDB
from coredb.boundary_db import FlowRateInletSpecification, BoundaryDB
from view.widgets.resizable_dialog import ResizableDialog
from .flow_rate_inlet_dialog_ui import Ui_FlowRateInletDialog
from .turbulence_model_helper import TurbulenceModelHelper
from .temperature_widget import TemperatureWidget


class FlowRateInletDialog(ResizableDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FlowRateInletDialog()
        self._ui.setupUi(self)

        self._specificationMethods = {
            FlowRateInletSpecification.VOLUME_FLOW_RATE.value: self.tr("Volume Flow Rate"),
            FlowRateInletSpecification.MASS_FLOW_RATE.value: self.tr("Mass Flow Rate"),
        }
        self._setupSpecificationMethodCombo()

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)
        self._turbulenceWidget = TurbulenceModelHelper.createWidget(self._xpath)
        self._temperatureWidget = TemperatureWidget(self._xpath, bcid)

        layout = self._ui.dialogContents.layout()
        if self._turbulenceWidget:
            layout.addWidget(self._turbulenceWidget)
        if ModelsDB.isEnergyModelOn():
            layout.addWidget(self._temperatureWidget)

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        path = self._xpath + '/flowRateInlet'

        writer = CoreDBWriter()
        specification = self._ui.flowRateSpecificationMethod.currentData()
        writer.append(path + '/flowRate/specification', specification, None)
        if specification == FlowRateInletSpecification.VOLUME_FLOW_RATE.value:
            writer.append(path + '/flowRate/volumeFlowRate', self._ui.volumeFlowRate.text(), self.tr("Volume Flow Rate"))
        elif specification == FlowRateInletSpecification.MASS_FLOW_RATE.value:
            writer.append(path + '/flowRate/massFlowRate', self._ui.massFlowRate.text(), self.tr("Mass Flow Rate"))

        if self._turbulenceWidget:
            self._turbulenceWidget.appendToWriter(writer)

        if not self._temperatureWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            self._temperatureWidget.rollbackWriting()
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self._temperatureWidget.completeWriting()
            super().accept()

    def _connectSignalsSlots(self):
        self._ui.flowRateSpecificationMethod.currentIndexChanged.connect(self._flowRateSpecificationMethodChanged)

    def _load(self):
        path = self._xpath + '/flowRateInlet'

        self._ui.flowRateSpecificationMethod.setCurrentText(
            self._specificationMethods[self._db.getValue(path + '/flowRate/specification')])
        self._ui.volumeFlowRate.setText(self._db.getValue(path + '/flowRate/volumeFlowRate'))
        self._ui.massFlowRate.setText(self._db.getValue(path + '/flowRate/massFlowRate'))
        self._flowRateSpecificationMethodChanged()

        if self._turbulenceWidget:
            self._turbulenceWidget.load()

        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()

    def _setupSpecificationMethodCombo(self):
        for value, text in self._specificationMethods.items():
            self._ui.flowRateSpecificationMethod.addItem(text, value)

    def _flowRateSpecificationMethodChanged(self):
        specification = self._ui.flowRateSpecificationMethod.currentData()
        self._ui.volumeFlowRateWidget.setVisible(
            specification == FlowRateInletSpecification.VOLUME_FLOW_RATE.value
        )
        self._ui.massFlowRateWidget.setVisible(
            specification == FlowRateInletSpecification.MASS_FLOW_RATE.value
        )
