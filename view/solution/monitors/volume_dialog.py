#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.cell_zone_db import CellZoneDB
from coredb.monitor_db import MonitorDB, VolumeReportType, FieldHelper
from view.widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem
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

        self._reportTypes = {
            VolumeReportType.VOLUME_AVERAGE.value: self.tr("Volume Average"),
            VolumeReportType.VOLUME_INTEGRAL.value: self.tr("Volume Integral"),
            VolumeReportType.MINIMUM.value: self.tr("Minimum"),
            VolumeReportType.MAXIMUM.value: self.tr("Maximum"),
            VolumeReportType.COEFFICIENT_OF_VARIATION.value: self.tr("Coefficient of Variation, CoV"),
        }

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
        self._volumes = None

        self._connectSignalsSlots()
        self._load()

    def getName(self):
        return self._name

    def accept(self):
        name = self._name
        if self._isNew:
            name = self._ui.name.text().strip()
            if not name:
                QMessageBox.critical(self, self.tr("Input Error"), self.tr("Enter Monitor Name."))
                return

        if not self._volumes:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select Volumes."))
            return

        writer = CoreDBWriter()
        writer.append(self._xpath + '/reportType', self._ui.reportType.currentData(), None)
        field = self._ui.fieldVariable.currentData()
        writer.append(self._xpath + '/field/field', field.field, None)
        writer.append(self._xpath + '/field/mid', field.mid, None)
        writer.append(self._xpath + '/volumes', ' '.join(v for v in self._volumes), self.tr("Volumes"))

        if self._isNew:
            writer.append(self._xpath + '/name', name, self.tr("Name"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
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
        self._ui.reportType.setCurrentText(self._reportTypes[self._db.getValue(self._xpath + '/reportType')])
        self._ui.fieldVariable.setCurrentText(
            FieldHelper.DBFieldKeyToText(self._db.getValue(self._xpath + '/field/field'),
                                         self._db.getValue(self._xpath + '/field/mid')))
        volumes = self._db.getValue(self._xpath + '/volumes')
        self._setVolumes(volumes.split() if volumes else [])

    def _setVolumes(self, volumes):
        self._volumes = volumes

        self._ui.volumes.clear()
        for v in volumes:
            self._ui.volumes.addItem(f'{CellZoneDB.getCellZoneName(v)} / {CellZoneDB.getCellZoneRegion(v)}')

    def _selectVolumes(self):
        self._dialog = MultiSelectorDialog(
            self, self.tr("Select Boundaries"),
            [SelectorItem(f'{c.name} / {c.rname}', c.name, c.id) for c in CellZoneDB.getCellZones()],
            self._volumes)
        self._dialog.open()
        self._dialog.accepted.connect(self._volumesChanged)

    def _volumesChanged(self):
        self._setVolumes(self._dialog.selectedItems())

    def _setupReportTypeCombo(self):
        for value, text in self._reportTypes.items():
            self._ui.reportType.addItem(text, value)

    def _setupFieldVariableCombo(self, fields):
        for f in fields:
            self._ui.fieldVariable.addItem(f.text, f.key)
