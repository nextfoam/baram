#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB
from coredb.monitor_db import MonitorDB, SurfaceReportType, FieldHelper
from view.widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem
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

        self._reportTypes = {
            SurfaceReportType.AREA_WEIGHTED_AVERAGE.value: self.tr("Area-Weighted Average"),
            SurfaceReportType.INTEGRAL.value: self.tr("Integral"),
            SurfaceReportType.FLOW_RATE.value: self.tr("Flow Rate"),
            SurfaceReportType.MINIMUM.value: self.tr("Minimum"),
            SurfaceReportType.MAXIMUM.value: self.tr("Maximum"),
            SurfaceReportType.COEFFICIENT_OF_VARIATION.value: self.tr("Coefficient of Variation, CoV"),
        }

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
        self._surfaces = None

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

        if not self._surfaces:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select Surfaces."))
            return

        writer = CoreDBWriter()
        writer.append(self._xpath + '/reportType', self._ui.reportType.currentData(), None)
        field = self._ui.fieldVariable.currentData()
        writer.append(self._xpath + '/field/field', field.field, None)
        writer.append(self._xpath + '/field/mid', field.mid, None)
        writer.append(self._xpath + '/surfaces', ' '.join(s for s in self._surfaces), self.tr("Surfaces"))

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
        self._ui.select.clicked.connect(self._selectSurfaces)

    def _load(self):
        self._ui.name.setText(self._name)
        self._ui.reportType.setCurrentText(self._reportTypes[self._db.getValue(self._xpath + '/reportType')])
        self._ui.fieldVariable.setCurrentText(
            FieldHelper.DBFieldKeyToText(self._db.getValue(self._xpath + '/field/field'),
                                         self._db.getValue(self._xpath + '/field/mid')))
        surfaces = self._db.getValue(self._xpath + '/surfaces')
        self._setSurfaces(surfaces.split() if surfaces else [])

    def _setSurfaces(self, surfaces):
        self._surfaces = surfaces

        self._ui.surfaces.clear()
        for s in surfaces:
            self._ui.surfaces.addItem(f'{BoundaryDB.getBoundaryName(s)} / {BoundaryDB.getBoundaryRegion(s)}')

    def _selectSurfaces(self):
        self._dialog = MultiSelectorDialog(
            self, self.tr("Select Boundaries"),
            [SelectorItem(b.toText(), b.name, b.id) for b in BoundaryDB.getBoundariesForSelector()], self._surfaces)
        self._dialog.open()
        self._dialog.accepted.connect(self._surfacesChanged)

    def _surfacesChanged(self):
        self._setSurfaces(self._dialog.selectedItems())

    def _setupReportTypeCombo(self):
        for value, text in self._reportTypes.items():
            self._ui.reportType.addItem(text, value)

    def _setupFieldVariableCombo(self, fields):
        for f in fields:
            self._ui.fieldVariable.addItem(f.text, f.key)
