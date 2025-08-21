#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.case_manager import CaseManager
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.material_schema import Phase
from baramFlow.coredb.region_db import RegionDB
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from .volume_dialog_ui import Ui_VolumeDialog


class VolumeDialog(QDialog):
    def __init__(self, parent, name=None):
        """Constructs volume monitor setup dialog.

        Args:
            name: Force Monitor name. If None, create a new monitor.
        """
        super().__init__(parent)
        self._ui = Ui_VolumeDialog()
        self._ui.setupUi(self)

        self._name = name
        self._isNew = False

        self._xpath = None
        self._volume = None

        for t in VolumeReportType:
            self._ui.reportType.addEnumItem(t, MonitorDB.volumeReportTypeToText(t))

        for f in FieldHelper.getAvailableFields():
            self._ui.fieldVariable.addItem(f.text, f.key)

        if name is None:
            db = coredb.CoreDB()
            self._name = db.addVolumeMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(name)

        self._xpath = MonitorDB.getVolumeMonitorXPath(self._name)

        self._connectSignalsSlots()
        self._load()

        if CaseManager().isRunning():
            self._ui.monitor.setEnabled(False)
            self._ui.ok.hide()
            self._ui.cancel.setText(self.tr('Close'))

    def getName(self):
        return self._name

    def reject(self):
        if self._isNew:
            db = coredb.CoreDB()
            db.removeVolumeMonitor(self._name)

        super().reject()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectVolumes)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(db.getValue(self._xpath + '/writeInterval'))
        self._ui.reportType.setCurrentData(VolumeReportType(db.getValue(self._xpath + '/reportType')))
        self._ui.fieldVariable.setCurrentText(
            FieldHelper.DBFieldKeyToText(Field(db.getValue(self._xpath + '/field/field')),
                                         db.getValue(self._xpath + '/field/fieldID')))
        volume = db.getValue(self._xpath + '/volume')
        if volume != '0':
            self._setVolume(volume)

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._name
        if self._isNew:
            name = self._ui.name.text().strip()
            if not name:
                await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Enter Monitor Name.'))
                return

        if not self._volume:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Volume.'))
            return

        field = self._ui.fieldVariable.currentData()
        region = CellZoneDB.getCellZoneRegion(self._volume)

        if RegionDB.getPhase(region) == Phase.SOLID and field.field != Field.TEMPERATURE:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Only temperature field can be configured for Solid Region.'))
            return

        if (field.field == Field.SCALAR
                and region != UserDefinedScalarsDB.getRegion(field.id)):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Volume.'))
            return

        try:
            with coredb.CoreDB() as db:
                db.setValue(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
                db.setValue(self._xpath + '/reportType', self._ui.reportType.currentValue())
                db.setValue(self._xpath + '/field/field', field.field.value)
                db.setValue(self._xpath + '/field/fieldID', field.id)
                db.setValue(self._xpath + '/volume', self._volume, self.tr('Volumes'))
        
                if self._isNew:
                    db.setValue(self._xpath + '/name', name, self.tr('Name'))
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

        self._name = name

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
