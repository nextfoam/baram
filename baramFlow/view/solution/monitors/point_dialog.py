#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from libbaram.mesh import Bounds
from widgets.async_message_box import AsyncMessageBox
from widgets.rendering.point_widget import PointWidget
from widgets.selector_dialog import SelectorDialog

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.mesh.vtk_loader import isPointInDataSet
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

        self._setupFieldCombo(FieldHelper.getAvailableFields())

        if name is None:
            db = coredb.CoreDB()
            self._name = db.addPointMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.groupBox.setTitle(name)

        self._xpath = MonitorDB.getPointMonitorXPath(self._name)

        self._pointWidget.outlineOff()
        self._pointWidget.setBounds(self._bounds)

        self._connectSignalsSlots()
        self._load()

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

    def _load(self):
        db = coredb.CoreDB()
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(db.getValue(self._xpath + '/writeInterval'))
        self._ui.field.setCurrentText(
            FieldHelper.DBFieldKeyToText(Field(db.getValue(self._xpath + '/field/field')),
                                         db.getValue(self._xpath + '/field/fieldID')))
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

        db = coredb.CoreDB()
        regions = db.getRegions()
        region = ''
        if len(regions) > 1:
            coordinate = (float(self._ui.coordinateX.text()),
                          float(self._ui.coordinateY.text()),
                          float(self._ui.coordinateZ.text()))

            for rname in regions:
                if isPointInDataSet(coordinate, app.internalMeshActor(rname).dataSet):
                    region = rname
                    break

        field = self._ui.field.currentData()
        if field.field == Field.SCALAR and region != UserDefinedScalarsDB.getRegion(field.id):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Point.'))
            return

        writer = CoreDBWriter()
        writer.append(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
        writer.append(self._xpath + '/field/field', field.field.value, None)
        writer.append(self._xpath + '/field/fieldID', field.id, None)
        writer.append(self._xpath + '/coordinate/x', self._ui.coordinateX.text(), self.tr("Coordinate X"))
        writer.append(self._xpath + '/coordinate/y', self._ui.coordinateY.text(), self.tr("Coordinate Y"))
        writer.append(self._xpath + '/coordinate/z', self._ui.coordinateZ.text(), self.tr("Coordinate Z"))
        writer.append(self._xpath + '/region', region, None)
        if self._snapOntoBoundary:
            writer.append(self._xpath + '/snapOntoBoundary', 'true', None)
            writer.append(self._xpath + '/boundary', self._snapOntoBoundary, None)
        else:
            writer.append(self._xpath + '/snapOntoBoundary', 'false', None)
            writer.append(self._xpath + '/boundary', '0', None)

        if self._isNew:
            writer.append(self._xpath + '/name', name, self.tr("Name"))

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            if self._isNew:
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

    def _setupFieldCombo(self, fields):
        for f in fields:
            self._ui.field.addItem(f.text, f.key)

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

