#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

import qasync
from PySide6.QtWidgets import QDialog

from libbaram.mesh import Bounds
from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox
from widgets.rendering.point_widget import PointWidget
from widgets.selector_dialog import SelectorDialog

from baramFlow.app import app
from baramFlow.base.base import Vector
from baramFlow.base.constants import FieldCategory
from baramFlow.base.field import TEMPERATURE, getFieldInstance
from baramFlow.base.material.material import Phase
from baramFlow.base.monitor.monitor import PointMonitorConfiguration, MonitorField
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.mesh.vtk_loader import isPointInDataSet
from baramFlow.services.monitor.monitor_service import MonitorService
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox, connectFieldsToComponents
from .point_dialog_ui import Ui_PointDialog


class PointDialog(QDialog):
    TEXT_FOR_NONE_BOUNDARY = 'None'

    def __init__(self, parent, uuid=None):
        """Constructs point monitor setup dialog.

        Args:
            uuid: Force Monitor ID. If None, create a new monitor.
        """
        super().__init__(parent)
        self._ui = Ui_PointDialog()
        self._ui.setupUi(self)

        self._uuid = uuid
        self._base = None
        self._isNew = False
        self._snapOntoBoundary = None

        self._renderingView = app.renderingView.view()
        self._bounds = Bounds(*self._renderingView.getBounds())
        self._pointWidget = PointWidget(self._renderingView)

        loadFieldsComboBox(self._ui.field)

        self._pointWidget.outlineOff()
        self._pointWidget.setBounds(self._bounds)

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
        if self._uuid is None:
            self._isNew = True
            data = MonitorService.newPointMonitor()
        else:
            data = MonitorService.getPointMonitor(self._uuid)
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(data.monitorBase.name)

        self._base = data.monitorBase
        self._ui.name.setText(data.monitorBase.name)
        self._ui.writeInterval.setText(data.monitorBase.writeInterval)

        self._ui.field.setCurrentIndex(self._ui.field.findData(data.field.field))
        self._ui.fieldComponent.setCurrentIndex(self._ui.fieldComponent.findData(data.field.component))
        self._ui.coordinateX.setPFloat(data.coordinate.x)
        self._ui.coordinateY.setPFloat(data.coordinate.y)
        self._ui.coordinateZ.setPFloat(data.coordinate.z)

        self._setSnapOntoBoundary(data.snapOntoBoundary)

        self._movePointWidget()
        self._pointWidget.on()

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
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Field.'))
            return

        db = coredb.CoreDB()
        regions = db.getRegions()
        region = None
        if self._snapOntoBoundary != '0':
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
            base = copy.deepcopy(self._base)
            base.name = name
            base.writeInterval = str(PFloat(self._ui.writeInterval.text(), self.tr('Write Interval'),
                                            low=0, lowInclusive=False))

            data = PointMonitorConfiguration(
                monitorBase=base,
                field=MonitorField(field=getFieldInstance(field.category, field.codeName),
                                   component=self._ui.fieldComponent.currentData()),
                coordinate=Vector(
                    self._ui.coordinateX.pFloat(self.tr('Coordinate X')),
                    self._ui.coordinateY.pFloat(self.tr('Coordinate Y')),
                    self._ui.coordinateZ.pFloat(self.tr('Coordinate Z'))),
                snapOntoBoundary=self._snapOntoBoundary,
                region=region)

            if self._isNew:
                MonitorService.addPointMonitor(data)
            else:
                MonitorService.updatePointMonitor(data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _setSnapOntoBoundary(self, bcid):
        if bcid is None or bcid == '0':
            self._ui.snapOntoBoundary.setText(self.TEXT_FOR_NONE_BOUNDARY)
            self._snapOntoBoundary = '0'
        else:
            self._ui.snapOntoBoundary.setText(BoundaryDB.getBoundaryText(bcid))
            self._snapOntoBoundary = bcid

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

