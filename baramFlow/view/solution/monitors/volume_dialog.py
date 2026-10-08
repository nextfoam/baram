#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

import qasync
from PySide6.QtWidgets import QDialog

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.constants import FieldCategory
from baramFlow.base.field import TEMPERATURE, getFieldInstance
from baramFlow.base.material.material import Phase
from baramFlow.base.monitor.monitor import VolumeMonitorConfiguration, MonitorField
from baramFlow.case_manager import CaseManager
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.services.monitor.monitor_service import MonitorService
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox, connectFieldsToComponents
from .volume_dialog_ui import Ui_VolumeDialog


class VolumeDialog(QDialog):
    def __init__(self, parent, uuid=None):
        super().__init__(parent)
        self._ui = Ui_VolumeDialog()
        self._ui.setupUi(self)

        self._uuid = uuid
        self._base = None
        self._isNew = False

        self._volume = None

        for t in VolumeReportType:
            self._ui.reportType.addItem(MonitorDB.volumeReportTypeToText(t), t)

        loadFieldsComboBox(self._ui.field)

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
        self._ui.select.clicked.connect(self._selectVolumes)
        self._ui.ok.clicked.connect(self._accept)

        connectFieldsToComponents(self._ui.field, self._ui.fieldComponent)

    def _load(self):
        if self._uuid is None:
            self._isNew = True
            data = MonitorService.newVolumeMonitor()
        else:
            data = MonitorService.getVolumeMonitor(self._uuid)
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(data.monitorBase.name)

        self._base = data.monitorBase
        self._ui.name.setText(data.monitorBase.name)
        self._ui.writeInterval.setText(data.monitorBase.writeInterval)

        self._ui.reportType.setCurrentIndex(self._ui.reportType.findData(data.reportType))
        self._ui.field.setCurrentIndex(self._ui.field.findData(data.field.field))
        self._ui.fieldComponent.setCurrentIndex(self._ui.fieldComponent.findData(data.field.component))

        if data.volume != '0':
            self._setVolume(data.volume)

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

        if not self._volume:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Volume.'))
            return

        region = CellZoneDB.getCellZoneRegion(self._volume)

        if RegionDB.getPhase(region) == Phase.SOLID and field != TEMPERATURE:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Only temperature field can be configured for Solid Region.'))
            return

        if field.category == FieldCategory.USER_SCALAR and region != UserDefinedScalarsDB.getRegion(field.codeName):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Volume.'))
            return

        try:
            base = copy.deepcopy(self._base)
            base.name = name
            base.writeInterval = str(PFloat(self._ui.writeInterval.text(), self.tr('Write Interval'),
                                            low=0, lowInclusive=False))

            data = VolumeMonitorConfiguration(
                monitorBase=base,
                reportType=self._ui.reportType.currentData(),
                field=MonitorField(field=getFieldInstance(field.category, field.codeName),
                                   component=self._ui.fieldComponent.currentData()),
                volume=self._volume
            )

            if self._isNew:
                MonitorService.addVolumeMonitor(data)
            else:
                MonitorService.updateVolumeMonitor(data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _setVolume(self, volume):
        self._volume = volume
        self._ui.volume.setText(CellZoneDB.getCellZoneText(volume))

    def _selectVolumes(self):
        self._dialog = SelectorDialog(self, self.tr("Select Cell Zone"), self.tr("Select Cell Zone"),
                                      CellZoneDB.getCellZoneSelectorItems())
        self._dialog.open()
        self._dialog.accepted.connect(self._volumeChanged)

    def _volumeChanged(self):
        self._setVolume(self._dialog.selectedItem())
