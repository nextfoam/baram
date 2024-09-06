#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
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

        self._name = name
        self._isNew = False

        self._xpath = None
        self._surface = None

        for t in SurfaceReportType:
            self._ui.reportType.addEnumItem(t, MonitorDB.surfaceReportTypeToText(t))

        for f in FieldHelper.getAvailableFields():
            self._ui.fieldVariable.addItem(f.text, f.key)

        if name is None:
            db = coredb.CoreDB()
            self._name = db.addSurfaceMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.groupBox.setTitle(name)

        self._xpath = MonitorDB.getSurfaceMonitorXPath(self._name)

        self._connectSignalsSlots()
        self._load()

    def getName(self):
        return self._name

    def reject(self):
        if self._isNew:
            db = coredb.CoreDB()
            db.removeSurfaceMonitor(self._name)

        super().reject()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSurface)
        self._ui.reportType.currentDataChanged.connect(self._reportTypeChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(db.getValue(self._xpath + '/writeInterval'))
        self._ui.reportType.setCurrentData(SurfaceReportType(db.getValue(self._xpath + '/reportType')))
        self._ui.fieldVariable.setCurrentText(
            FieldHelper.DBFieldKeyToText(Field(db.getValue(self._xpath + '/field/field')),
                                         db.getValue(self._xpath + '/field/fieldID')))
        surface = db.getValue(self._xpath + '/surface')
        if surface != '0':
            self._setSurface(surface)

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._name
        if self._isNew:
            name = self._ui.name.text().strip()
            if not name:
                await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Enter Monitor Name."))
                return

        if not self._surface:
            await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Select Surface."))
            return

        field = self._ui.fieldVariable.currentData()
        if (field.field == Field.SCALAR
                and BoundaryDB.getBoundaryRegion(self._surface) != UserDefinedScalarsDB.getRegion(field.id)):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Surface.'))
            return

        writer = CoreDBWriter()
        writer.append(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
        writer.append(self._xpath + '/reportType', self._ui.reportType.currentValue(), None)
        writer.append(self._xpath + '/field/field', field.field.value, None)
        writer.append(self._xpath + '/field/fieldID', field.id, None)
        writer.append(self._xpath + '/surface', self._surface, self.tr("Surface"))

        if self._isNew:
            writer.append(self._xpath + '/name', name, self.tr("Name"))

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            if self._isNew:
                self._name = name

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

    def _reportTypeChanged(self, reportType):
        self._ui.fieldVariable.setDisabled(
            reportType == SurfaceReportType.MASS_FLOW_RATE or reportType == SurfaceReportType.VOLUME_FLOW_RATE)
