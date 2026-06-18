#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.boundary.boundary_patch import PressureOutletUpdate
from baramFlow.base.boundary.pressure_port import PressureOutlet
from baramFlow.base.material.material import Phase, DensitySpecification, SpecificHeatSpecification
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .pressure_outlet_dialog_ui import Ui_PressureOutletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class PressureOutletDialog(ResizableDialog):
    RELATIVE_XPATH = '/pressureOutlet'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_PressureOutletDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = None
        self._volumeFractionWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        layout = self._ui.calculateBackflow.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._volumeFractionWidget = ConditionalWidgetHelper.volumeFractionWidget(rname, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)

        mid = RegionDB.getMaterial(rname)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(mid, layout)

        db = coredb.CoreDB()
        xpath = MaterialDB.getXPath(mid)
        if (not ModelsDB.isEnergyModelOn()
                or MaterialDB.getPhase(mid) == Phase.SOLID
                or DensitySpecification(db.getValue(xpath + '/density/specification')) != DensitySpecification.PERFECT_GAS
                or SpecificHeatSpecification(db.getValue(xpath + '/specificHeat/specification')) != SpecificHeatSpecification.CONSTANT):
            self._ui.NRB.hide()

            if not ModelsDB.isEnergyModelOn():
                if self._turbulenceWidget.on() or self._volumeFractionWidget.on() or self._scalarsWidget.on():
                    # Hides only the total temperature item when the energy model is turned off and some items are enabled.
                    self._ui.backflowTotalTemperatureWidget.hide()
                else:
                    # Hides the entire Backflow Calculation groupbox when the energy model is turned off and all items are disabled.
                    self._ui.calculateBackflow.hide()

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

        writer = None
        turbulence = None

        try:
            if self._ui.calculateBackflow.isChecked():
                writer = CoreDBWriter()

                if not self._turbulenceWidget.appendToWriter(writer):
                    return

                if not await self._volumeFractionWidget.appendToWriter(writer, self._xpath + '/volumeFractions'):
                    return

                if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
                    return

                if not await self._speciesWidget.appendToWriter(writer, self._xpath + '/species'):
                    return

                turbulence = self._turbulenceWidget.data()

            data = PressureOutletUpdate(
                pressureOutlet=PressureOutlet(
                    totalPressure=PFloat(self._ui.totalPressure.text(), self.tr("Total Pressure")),
                    nonReflective=self._ui.nonReflectingBoundary.isChecked(),
                    calculatedBackflow=self._ui.calculateBackflow.isChecked(),
                    backflowTotalTemperature=PFloat(self._ui.backflowTotalTemperature.text(),
                                                    self.tr("Backflow Total Temperature"))),
                turbulence=turbulence)

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.totalPressure.setText(db.getValue(xpath + '/totalPressure'))

        self._ui.calculateBackflow.setChecked(db.getValue(xpath + '/calculatedBackflow') == "true")
        self._turbulenceWidget.load()
        self._ui.nonReflectingBoundary.setChecked(db.getValue(xpath + '/nonReflective') == 'true')
        self._ui.backflowTotalTemperature.setText(db.getValue(xpath + '/backflowTotalTemperature'))
        self._volumeFractionWidget.load(self._xpath + '/volumeFractions')
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
