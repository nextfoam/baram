#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

import qasync
from PySide6.QtWidgets import QDialog

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.base import DirectionSpecificationMethod, DirectionSpecificationMethodTexts, Vector
from baramFlow.base.monitor.monitor import MonitorManager, ForceMonitorConfiguration
from baramFlow.base.monitor.monitor import ForceDirection
from baramFlow.case_manager import CaseManager
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.widgets.region_objects_selector import BoundariesSelector

from .force_dialog_ui import Ui_ForceDialog


class ForceDialog(QDialog):
    def __init__(self, parent, uuid=None):
        super().__init__(parent)
        self._ui = Ui_ForceDialog()
        self._ui.setupUi(self)

        self._uuid = uuid
        self._base = None
        self._region = None
        self._isNew = False

        self._boundaries = None

        for method in DirectionSpecificationMethod:
            self._ui.specificationMethod.addItem(DirectionSpecificationMethodTexts[method], method)

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

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._onSpecificationMethodChanged)
        self._ui.select.clicked.connect(self._selectBoundaries)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        if self._uuid is None:
            self._isNew = True
            data = MonitorManager.newForceMonitor()
        else:
            data = MonitorManager.getForceMonitor(self._uuid)
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(data.monitorBase.name)

        self._base = data.monitorBase
        self._ui.name.setText(data.monitorBase.name)
        self._ui.writeInterval.setText(data.monitorBase.writeInterval)

        self._ui.specificationMethod.setCurrentIndex(
            self._ui.specificationMethod.findData(data.forceDirection.specificationMethod))
        self._ui.dragDirectionX.setPFloat(data.forceDirection.dragDirection.x)
        self._ui.dragDirectionY.setPFloat(data.forceDirection.dragDirection.y)
        self._ui.dragDirectionZ.setPFloat(data.forceDirection.dragDirection.z)
        self._ui.liftDirectionX.setPFloat(data.forceDirection.liftDirection.x)
        self._ui.liftDirectionY.setPFloat(data.forceDirection.liftDirection.y)
        self._ui.liftDirectionZ.setPFloat(data.forceDirection.liftDirection.z)
        self._ui.AoA.setPFloat(data.forceDirection.angleOfAttack)
        self._ui.AoS.setPFloat(data.forceDirection.angleOfSideslip)

        self._ui.centerOfRotationX.setPFloat(data.centerOfRotation.x)
        self._ui.centerOfRotationY.setPFloat(data.centerOfRotation.y)
        self._ui.centerOfRotationZ.setPFloat(data.centerOfRotation.z)
        self._region = data.region
        self._setBoundaries(data.boundaries)

        self._onSpecificationMethodChanged()

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text().strip()
        if name == '':
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Enter Monitor Name.'))
            return

        if name != self._base.name and MonitorManager.isExistingName(name):
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Name "{0}" already exist.'.format(name)))
            return

        if not self._boundaries:
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Select Boundaries.'))
            return

        try:
            base = copy.deepcopy(self._base)
            base.name = name
            base.writeInterval = str(PFloat(self._ui.writeInterval.text(), self.tr('Write Interval'),
                                            low=0, lowInclusive=False))

            forceDirection = ForceDirection(
                specificationMethod=self._ui.specificationMethod.currentData(),
                dragDirection=Vector(self._ui.dragDirectionX.pFloat(self.tr('Drag Direction')),
                                     self._ui.dragDirectionY.pFloat(self.tr('Drag Direction')),
                                     self._ui.dragDirectionZ.pFloat(self.tr('Drag Direction'))),
                liftDirection=Vector(self._ui.liftDirectionX.pFloat(self.tr('Lift Direction')),
                                     self._ui.liftDirectionY.pFloat(self.tr('Lift Direction')),
                                     self._ui.liftDirectionZ.pFloat(self.tr('Lift Direction'))))
            if forceDirection.specificationMethod == DirectionSpecificationMethod.AOA_AOS:
                forceDirection.angleOfAttack = self._ui.AoA.pFloat(self.tr('Angle of Attack'))
                forceDirection.angleOfSideslip = self._ui.AoS.pFloat(self.tr('Angle of Sideslip'))

            data = ForceMonitorConfiguration(
                monitorBase=base,
                forceDirection=forceDirection,
                centerOfRotation=Vector(
                    self._ui.centerOfRotationX.pFloat(self.tr('Center of Rotation X')),
                    self._ui.centerOfRotationY.pFloat(self.tr('Center of Rotation Y')),
                    self._ui.centerOfRotationZ.pFloat(self.tr('Center of Rotation Z'))),
                region=self._region,
                boundaries=self._boundaries)

            if self._isNew:
                MonitorManager.addForceMonitor(data)
            else:
                MonitorManager.updateForceMonitor(data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        super().accept()

    def _setBoundaries(self, boundaries):
        self._boundaries = boundaries

        self._ui.boundaries.clear()
        for bcid in boundaries:
            self._ui.boundaries.addItem(BoundaryDB.getBoundaryText(bcid))

    def _selectBoundaries(self):
        self._dialog = BoundariesSelector(self, self._boundaries)
        self._dialog.accepted.connect(self._boundariesChanged)
        self._dialog.open()

    def _boundariesChanged(self):
        self._region = self._dialog.region()
        self._setBoundaries(self._dialog.selectedItems())

    def _onSpecificationMethodChanged(self):
        method = self._ui.specificationMethod.currentData()
        if method == DirectionSpecificationMethod.DIRECT:
            self._ui.direction.setTitle(self.tr('Direction'))
            self._ui.angles.hide()
        else:
            self._ui.direction.setTitle(self.tr('Direction at AOA=0, AOS=0'))
            self._ui.angles.show()
