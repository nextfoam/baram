#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

import qasync
from PySide6.QtWidgets import QDialog

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.constants import FieldCategory
from baramFlow.base.field import Field, FieldType, TEMPERATURE, getFieldInstance, ALL_PHASES, ALL_SPECIES
from baramFlow.base.material.material import Phase
from baramFlow.case_manager import CaseManager
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.base.monitor.monitor import SurfaceMonitorConfiguration, MonitorField
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.services.monitor.monitor_policy import MonitorPolicy
from baramFlow.services.monitor.monitor_service import MonitorService
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox
from .surface_dialog_ui import Ui_SurfaceDialog


class SurfaceDialog(QDialog):
    def __init__(self, parent, uuid=None):
        super().__init__(parent)
        self._ui = Ui_SurfaceDialog()
        self._ui.setupUi(self)

        self._uuid = uuid
        self._base = None
        self._isNew = False

        self._surface = None

        for t in SurfaceReportType:
             self._ui.reportType.addItem(MonitorDB.surfaceReportTypeToText(t), t)

        loadFieldsComboBox(self._ui.field)
        if ModelsDB.isMultiphaseModelOn():
            self._ui.field.insertItem(0, self.tr('<Fluid>'), ALL_PHASES)
        else:
            self._ui.field.insertItem(0, self.tr('<Fluid>'), ALL_SPECIES)

        self._connectSignalsSlots()
        self._load()

        if CaseManager().isRunning():
            self._ui.monitor.setEnabled(False)
            self._ui.ok.hide()
            self._ui.cancel.setText(self.tr('Close'))

    def getID(self):
        return self._base.uuid

    def reject(self):
        super().reject()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSurface)
        self._ui.reportType.currentIndexChanged.connect(self._updateInputFields)
        self._ui.field.currentIndexChanged.connect(self._updateInputFields)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        if self._uuid is None:
            self._isNew = True
            data = MonitorService.newSurfaceMonitor()
        else:
            data = MonitorService.getSurfaceMonitor(self._uuid)
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(data.monitorBase.name)

        self._base = data.monitorBase
        self._ui.name.setText(data.monitorBase.name)
        self._ui.writeInterval.setText(data.monitorBase.writeInterval)

        self._ui.reportType.setCurrentIndex(self._ui.reportType.findData(data.reportType))
        self._ui.field.setCurrentIndex(self._ui.field.findData(data.field.field))
        self._ui.fieldComponent.setCurrentIndex(self._ui.fieldComponent.findData(data.field.component))

        if data.surface != '0':
            self._setSurface(data.surface)

        self._updateInputFields()

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if not name:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Enter Monitor Name.'))
            return

        if name != self._base.name and MonitorService.isExistingName(name):
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Name "{0}" already exist.'.format(name)))
            return

        field = self._ui.field.currentData()
        if field is None:
            await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Select Field."))
            return

        reportType = self._ui.reportType.currentData()
        if (reportType == SurfaceReportType.VOLUME_FLOW_RATE
                and field.category == FieldCategory.SPECIE and field != ALL_SPECIES):
            await AsyncMessageBox().information(
                self, self.tr("Input Error"),
                self.tr("Volume Flow Rate does not support individual species."))
            return

        if not self._surface:
            await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Select Surface."))
            return

        region = BoundaryDB.getBoundaryRegion(self._surface)

        if RegionDB.getPhase(region) == Phase.SOLID and field != TEMPERATURE:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Only temperature field can be configured for Solid Region.'))
            return

        if field.category == FieldCategory.USER_SCALAR and region != UserDefinedScalarsDB.getRegion(field.codeName):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Surface.'))
            return

        try:
            base = copy.deepcopy(self._base)
            base.name = name
            base.writeInterval = str(PFloat(self._ui.writeInterval.text(), self.tr('Write Interval'),
                                            low=0, lowInclusive=False))

            data = SurfaceMonitorConfiguration(
                monitorBase=base,
                reportType=reportType,
                field=MonitorField(field=getFieldInstance(field.category, field.codeName),
                                   component=self._ui.fieldComponent.currentData()),
                surface=self._surface
            )

            MonitorPolicy.validateSurfaceMonitor(data)

            if self._isNew:
                MonitorService.addSurfaceMonitor(data)
            else:
                MonitorService.updateSurfaceMonitor(data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _setSurface(self, surface):
        self._surface = surface
        self._ui.surface.setText(BoundaryDB.getBoundaryText(surface))

    def _selectSurface(self):
        self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                      BoundaryDB.getBoundarySelectorItems())
        self._dialog.accepted.connect(self._surfaceChanged)
        self._dialog.open()

    def _surfaceChanged(self):
        self._setSurface(self._dialog.selectedItem())

    def _updateInputFields(self):
        reportType: SurfaceReportType = self._ui.reportType.currentData()
        isFlowRateType = reportType in [SurfaceReportType.MASS_FLOW_RATE, SurfaceReportType.VOLUME_FLOW_RATE]
        hasMultiMaterials = ModelsDB.isMultiphaseModelOn() or ModelsDB.isSpeciesModelOn()

        # Field Category to keep without hiding
        category = None
        # Hide other category fields only if report type is MASS_FLOW_RATE or VOLUME_FLOW_RATE
        if isFlowRateType:
            if ModelsDB.isMultiphaseModelOn():
                category = FieldCategory.PHASE
            elif ModelsDB.isSpeciesModelOn():
                category = FieldCategory.SPECIE

        self._ui.field.view().setRowHidden(0, not isFlowRateType)
        for i in range(1, self._ui.field.count()):
            self._ui.field.view().setRowHidden(i,
                                               category is not None and self._ui.field.itemData(i).category != category)

        if isFlowRateType and not hasMultiMaterials:
            self._ui.field.setCurrentIndex(0)   # All Regions have single material. Select ALL_SPECIES
        else:
            if self._ui.field.view().isRowHidden(self._ui.field.currentIndex()):
                if self._ui.field.currentIndex() == 0:
                    self._ui.field.setCurrentIndex(1)
                else:
                    self._ui.field.setCurrentIndex(0)

        self._ui.field.setEnabled(not isFlowRateType or hasMultiMaterials)

        field: Field = self._ui.field.currentData()
        if field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
        else:
            self._ui.fieldComponent.setEnabled(False)
