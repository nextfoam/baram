#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.base.monitor.monitor import getMonitorField
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.constants import FieldCategory, VectorComponent
from baramFlow.base.field import VELOCITY, TEMPERATURE
from baramFlow.base.material.material import Phase
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox, connectFieldsToComponents
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
            self._ui.reportType.addItem(MonitorDB.surfaceReportTypeToText(t), t)

        loadFieldsComboBox(self._ui.field)

        if name is None:
            db = coredb.CoreDB()
            self._name = db.addSurfaceMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(name)

        self._xpath = MonitorDB.getSurfaceMonitorXPath(self._name)

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
            db.removeSurfaceMonitor(self._name)

        super().reject()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSurface)
        self._ui.reportType.currentIndexChanged.connect(self._reportTypeChanged)
        self._ui.ok.clicked.connect(self._accept)

        connectFieldsToComponents(self._ui.field, self._ui.fieldComponent)

    def _load(self):
        db = coredb.CoreDB()
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(db.getValue(self._xpath + '/writeInterval'))
        self._ui.reportType.setCurrentIndex(
            self._ui.reportType.findData(SurfaceReportType(db.getValue(self._xpath + '/reportType'))))

        field = getMonitorField(MonitorDB.getSurfaceMonitorXPath(self._name))
        self._ui.field.setCurrentIndex(self._ui.field.findData(field.field))
        self._ui.fieldComponent.setCurrentIndex(self._ui.fieldComponent.findData(field.component))

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

        field = self._ui.field.currentData()
        if field is None:
            await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Select Field."))
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
            with coredb.CoreDB() as db:
                db.setValue(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
                db.setValue(self._xpath + '/reportType', self._ui.reportType.currentData().value)
                db.setValue(self._xpath + '/fieldCategory', field.category.value)
                db.setValue(self._xpath + '/fieldCodeName', field.codeName)
                db.setValue(self._xpath + '/fieldComponent', str(self._ui.fieldComponent.currentData().value))
                db.setValue(self._xpath + '/surface', self._surface, self.tr("Surface"))
                print(field.codeName)
        
                if self._isNew:
                    db.setValue(self._xpath + '/name', name, self.tr("Name"))
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

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

    def _reportTypeChanged(self, index):
        if self._ui.reportType.currentData() in (SurfaceReportType.MASS_FLOW_RATE, SurfaceReportType.VOLUME_FLOW_RATE):
            self._ui.field.setEnabled(False)
            self._ui.fieldComponent.setEnabled(False)
            self._ui.field.setCurrentIndex(self._ui.field.findData(VELOCITY))
            self._ui.fieldComponent.setCurrentIndex(self._ui.fieldComponent.findData(VectorComponent.MAGNITUDE))
        else:
            self._ui.field.setEnabled(True)
            self._ui.fieldComponent.setEnabled(True)
