#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.monitor_db import MonitorDB, SurfaceReportType, FieldHelper
from baramFlow.view.widgets.selector_dialog import SelectorDialog
from .surface_dialog_ui import Ui_SurfaceDialog


class SurfaceDialog(QDialog):
    def __init__(self, parent, name=None):
        """Constructs surface monitor setup dialog.

        Args:
            name: Force Monitor name. If None, create a new monitor.
        """
        super().__init__(parent)
        self._ui = Ui_SurfaceDialog()
        self._ui.setupUi(self)

        self._setupReportTypeCombo()
        self._setupFieldVariableCombo(FieldHelper.getAvailableFields())

        self._name = name
        self._isNew = False
        self._db = coredb.CoreDB()

        if name is None:
            self._name = self._db.addSurfaceMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.groupBox.setTitle(name)

        self._xpath = MonitorDB.getSurfaceMonitorXPath(self._name)
        self._surface = None

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

        if not self._surface:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select Surface."))
            return

        writer = CoreDBWriter()
        writer.append(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
        writer.append(self._xpath + '/reportType', self._ui.reportType.currentData(), None)
        field = self._ui.fieldVariable.currentData()
        writer.append(self._xpath + '/field/field', field.field, None)
        writer.append(self._xpath + '/field/mid', field.mid, None)
        writer.append(self._xpath + '/surface', self._surface, self.tr("Surface"))

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
            self._db.removeSurfaceMonitor(self._name)

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSurface)
        self._ui.reportType.currentTextChanged.connect(self._reportTypeChanged)

    def _load(self):
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(self._db.getValue(self._xpath + '/writeInterval'))
        self._ui.reportType.setCurrentText(MonitorDB.dbSurfaceReportTypeToText(self._db.getValue(self._xpath + '/reportType')))
        self._ui.fieldVariable.setCurrentText(
            FieldHelper.DBFieldKeyToText(self._db.getValue(self._xpath + '/field/field'),
                                         self._db.getValue(self._xpath + '/field/mid')))
        surface = self._db.getValue(self._xpath + '/surface')
        if surface != '0':
            self._setSurface(surface)

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

    def _setupReportTypeCombo(self):
        for type_ in SurfaceReportType:
            self._ui.reportType.addItem(MonitorDB.dbSurfaceReportTypeToText(type_.value), type_.value)

    def _setupFieldVariableCombo(self, fields):
        for f in fields:
            self._ui.fieldVariable.addItem(f.text, f.key)

    def _reportTypeChanged(self):
        self._ui.fieldVariable.setDisabled(
            self._ui.reportType.currentData() == SurfaceReportType.MASS_FLOW_RATE.value
            or self._ui.reportType.currentData() == SurfaceReportType.VOLUME_FLOW_RATE.value)
