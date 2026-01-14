#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.base.constants import FieldCategory
from baramFlow.base.field import TEMPERATURE
from baramFlow.base.monitor.monitor import getMonitorField
from libbaram.mesh import Bounds
from widgets.async_message_box import AsyncMessageBox
from widgets.rendering.point_widget import PointWidget
from widgets.selector_dialog import SelectorDialog

from baramFlow.app import app
from baramFlow.base.material.material import Phase
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.mesh.vtk_loader import isPointInDataSet
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox, connectFieldsToComponents
from .point_dialog_ui import Ui_PointDialog


class PointDialog(QDialog):
    TEXT_FOR_NONE_BOUNDARY = 'None'

    def __init__(self, parent, name=None):
        """Constructs point monitor setup dialog.

        Args:
            name: Force Monitor name. If None, create a new monitor.
        """
        super().__init__(parent)
        self._ui = Ui_PointDialog()
        self._ui.setupUi(self)

        self._name = name
        self._isNew = False
        self._xpath = None
        self._snapOntoBoundary = None

        self._renderingView = app.renderingView.view()
        self._bounds = Bounds(*self._renderingView.getBounds())
        self._pointWidget = PointWidget(self._renderingView)

        loadFieldsComboBox(self._ui.field)

        if name is None:
            db = coredb.CoreDB()
            self._name = db.addPointMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(name)

        self._xpath = MonitorDB.getPointMonitorXPath(self._name)

        self._pointWidget.outlineOff()
        self._pointWidget.setBounds(self._bounds)

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
            db.removePointMonitor(self._name)

        super().reject()

    def done(self, result):
        self._pointWidget.off()

        super().done(result)

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSnapOntoBoundary)
        self._ui.coordinateX.editingFinished.connect(self._movePointWidget)
        self._ui.coordinateY.editingFinished.connect(self._movePointWidget)
        self._ui.coordinateZ.editingFinished.connect(self._movePointWidget)
        self._ui.ok.clicked.connect(self._accept)

        connectFieldsToComponents(self._ui.field, self._ui.fieldComponent)

    def _load(self):
        db = coredb.CoreDB()
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(db.getValue(self._xpath + '/writeInterval'))

        field = getMonitorField(MonitorDB.getPointMonitorXPath(self._name))
        self._ui.field.setCurrentIndex(self._ui.field.findData(field.field))
        self._ui.fieldComponent.setCurrentIndex(self._ui.fieldComponent.findData(field.component))

        self._ui.coordinateX.setText(db.getValue(self._xpath + '/coordinate/x'))
        self._ui.coordinateY.setText(db.getValue(self._xpath + '/coordinate/y'))
        self._ui.coordinateZ.setText(db.getValue(self._xpath + '/coordinate/z'))
        snapOntoBoundary = db.getValue(self._xpath + '/snapOntoBoundary')
        if snapOntoBoundary == 'true':
            self._setSnapOntoBoundary(db.getValue(self._xpath + '/boundary'))
        else:
            self._setSnapOntoBoundary(None)

        self._movePointWidget()
        self._pointWidget.on()

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

        db = coredb.CoreDB()
        regions = db.getRegions()
        region = None
        if self._snapOntoBoundary:
            region = BoundaryDB.getBoundaryRegion(self._snapOntoBoundary)
        else:
            coordinate = (float(self._ui.coordinateX.text()),
                          float(self._ui.coordinateY.text()),
                          float(self._ui.coordinateZ.text()))

            for rname in regions:
                if isPointInDataSet(coordinate, app.internalMeshActor(rname).dataSet):
                    region = rname
                    break

        if region is None:
            await AsyncMessageBox().information(self, self.tr('Input Erropr'), self.tr('Select Point in a region'))
            return

        if RegionDB.getPhase(region) == Phase.SOLID and field != TEMPERATURE:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Only temperature field can be configured for Solid Region.'))
            return

        if field.category == FieldCategory.USER_SCALAR and region != UserDefinedScalarsDB.getRegion(field.codeName):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Point.'))
            return

        try:
            with coredb.CoreDB() as db:
                db.setValue(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
                db.setValue(self._xpath + '/fieldCategory', field.category.value)
                db.setValue(self._xpath + '/fieldCodeName', field.codeName)
                db.setValue(self._xpath + '/fieldComponent', str(self._ui.fieldComponent.currentData().value))
                db.setValue(self._xpath + '/coordinate/x', self._ui.coordinateX.text(), self.tr("Coordinate X"))
                db.setValue(self._xpath + '/coordinate/y', self._ui.coordinateY.text(), self.tr("Coordinate Y"))
                db.setValue(self._xpath + '/coordinate/z', self._ui.coordinateZ.text(), self.tr("Coordinate Z"))
                db.setValue(self._xpath + '/region', region)
                if self._snapOntoBoundary:
                    db.setValue(self._xpath + '/snapOntoBoundary', 'true')
                    db.setValue(self._xpath + '/boundary', self._snapOntoBoundary)
                else:
                    db.setValue(self._xpath + '/snapOntoBoundary', 'false')
                    db.setValue(self._xpath + '/boundary', '0')

                if self._isNew:
                    db.setValue(self._xpath + '/name', name, self.tr("Name"))
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

        self._name = name

        self.accept()

    def _setSnapOntoBoundary(self, bcid):
        self._snapOntoBoundary = bcid
        if bcid is None:
            self._ui.snapOntoBoundary.setText(self.TEXT_FOR_NONE_BOUNDARY)
        else:
            self._ui.snapOntoBoundary.setText(BoundaryDB.getBoundaryText(bcid))

    def _selectSnapOntoBoundary(self):
        self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                      BoundaryDB.getBoundarySelectorItems(), self.TEXT_FOR_NONE_BOUNDARY)
        self._dialog.accepted.connect(self._snapOntoBoundaryChanged)
        self._dialog.open()

    def _snapOntoBoundaryChanged(self):
        self._setSnapOntoBoundary(self._dialog.selectedItem())

    def _movePointWidget(self):
        try:
            point = (
                float(self._ui.coordinateX.text()),
                float(self._ui.coordinateY.text()),
                float(self._ui.coordinateZ.text())
            )

            if self._bounds.includes(point):
                self._pointWidget.setPosition(*point)
                self._pointWidget.on()
            else:
                self._pointWidget.off()
        except Exception:
            self._pointWidget.off()

