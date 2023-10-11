#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.monitor_db import MonitorDB, VolumeReportType, FieldHelper
from baramFlow.view.widgets.selector_dialog import SelectorDialog
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

        self._setupReportTypeCombo()
        self._setupFieldVariableCombo(FieldHelper.getAvailableFields())

        self._name = name
        self._isNew = False
        self._db = coredb.CoreDB()

        if name is None:
            self._name = self._db.addVolumeMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.groupBox.setTitle(name)

        self._xpath = MonitorDB.getVolumeMonitorXPath(self._name)
        self._volume = None

        self._connectSignalsSlots()
        self._load()

    def getName(self):
        return self._name

    def accept(self):
        name = self._name
        if self._isNew:
            name = self._ui.name.text().strip()
            if not name:
                QMessageBox.critical(self, self.tr('Input Error'), self.tr('Enter Monitor Name.'))
                return

        if not self._volume:
            QMessageBox.critical(self, self.tr('Input Error'), self.tr('Select Volume.'))
            return

        writer = CoreDBWriter()
        writer.append(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
        writer.append(self._xpath + '/reportType', self._ui.reportType.currentData(), None)
        field = self._ui.fieldVariable.currentData()
        writer.append(self._xpath + '/field/field', field.field, None)
        writer.append(self._xpath + '/field/mid', field.mid, None)
        writer.append(self._xpath + '/volume', self._volume, self.tr('Volumes'))

        if self._isNew:
            writer.append(self._xpath + '/name', name, self.tr('Name'))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
        else:
            if self._isNew:
                self._name = name

            super().accept()

    def reject(self):
        super().reject()
        if self._isNew:
            self._db.removeVolumeMonitor(self._name)

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectVolumes)

    def _load(self):
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(self._db.getValue(self._xpath + '/writeInterval'))
        self._ui.reportType.setCurrentText(
            MonitorDB.dbVolumeReportTypeToText(self._db.getValue(self._xpath + '/reportType')))
        self._ui.fieldVariable.setCurrentText(
            FieldHelper.DBFieldKeyToText(self._db.getValue(self._xpath + '/field/field'),
                                         self._db.getValue(self._xpath + '/field/mid')))
        volume = self._db.getValue(self._xpath + '/volume')
        if volume != '0':
            self._setVolume(volume)

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

    def _setupReportTypeCombo(self):
        for type_ in VolumeReportType:
            self._ui.reportType.addItem(MonitorDB.dbVolumeReportTypeToText(type_.value), type_.value)

    def _setupFieldVariableCombo(self, fields):
        for f in fields:
            self._ui.fieldVariable.addItem(f.text, f.key)
