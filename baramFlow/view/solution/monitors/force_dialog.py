#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.monitor_db import MonitorDB, DirectionSpecificationMethod
from baramFlow.view.widgets.region_objects_selector import BoundariesSelector
from widgets.async_message_box import AsyncMessageBox

from .force_dialog_ui import Ui_ForceDialog


class ForceDialog(QDialog):
    def __init__(self, parent, name=None):
        """Constructs force monitor setup dialog.

        Args:
            name: Force Monitor name. If None, create a new monitor.
        """
        super().__init__(parent)
        self._ui = Ui_ForceDialog()
        self._ui.setupUi(self)

        self._name = name
        self._region = None
        self._isNew = False

        self._xpath = None
        self._boundaries = None

        self._ui.specificationMethod.addEnumItems({
            DirectionSpecificationMethod.DIRECT:    self.tr('Direct'),
            DirectionSpecificationMethod.AOA_AOS:   self.tr('AOA and AOS')
        })

        if name is None:
            db = coredb.CoreDB()
            self._name = db.addForceMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.monitor.setTitle(name)

        self._xpath = MonitorDB.getForceMonitorXPath(self._name)

        self._connectSignalsSlots()
        self._load()

        if CaseManager().isRunning():
            self._ui.monitor.setEnabled(False)
            self._ui.ok.hide()
            self._ui.cancel.setText(self.tr('Close'))

    def getName(self):
        return self._name

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._name
        if self._isNew:
            name = self._ui.name.text().strip()
            if not name:
                await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Enter Monitor Name."))
                return

        if not self._boundaries:
            await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Select Boundaries."))
            return

        try:
            with coredb.CoreDB() as db:
                db.setValue(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))

                specificationMethod = self._ui.specificationMethod.currentData()
                db.setValue(self._xpath + '/forceDirection/specificationMethod', specificationMethod.value)
                db.setValue(self._xpath + '/forceDirection/dragDirection/x', self._ui.dragDirectionX.text(),
                              self.tr('Drag Direction'))
                db.setValue(self._xpath + '/forceDirection/dragDirection/y', self._ui.dragDirectionY.text(),
                              self.tr('Drag Direction'))
                db.setValue(self._xpath + '/forceDirection/dragDirection/z', self._ui.dragDirectionZ.text(),
                              self.tr('Drag Direction'))
                db.setValue(self._xpath + '/forceDirection/liftDirection/x', self._ui.liftDirectionX.text(),
                              self.tr('Lift Direction'))
                db.setValue(self._xpath + '/forceDirection/liftDirection/y', self._ui.liftDirectionY.text(),
                              self.tr('Lift Direction'))
                db.setValue(self._xpath + '/forceDirection/liftDirection/z', self._ui.liftDirectionZ.text(),
                              self.tr('Lift Direction'))
                db.setValue(self._xpath + '/forceDirection/angleOfAttack', self._ui.AoA.text(),
                            self.tr('Angle of Attack'))
                db.setValue(self._xpath + '/forceDirection/angleOfSideslip', self._ui.AoS.text(),
                            self.tr('Angle of Sideslip'))
                if specificationMethod == DirectionSpecificationMethod.AOA_AOS:
                    db.setValue(self._xpath + '/forceDirection/angleOfAttack', self._ui.AoA.text(),
                                self.tr('Angle of Attack'))
                    db.setValue(self._xpath + '/forceDirection/angleOfSideslip', self._ui.AoS.text(),
                                  self.tr('Angle of Sideslip'))

                db.setValue(self._xpath + '/centerOfRotation/x',
                              self._ui.centerOfRotationX.text(), self.tr("Center of Rotation X"))
                db.setValue(self._xpath + '/centerOfRotation/y',
                              self._ui.centerOfRotationY.text(), self.tr("Center of Rotation Y"))
                db.setValue(self._xpath + '/centerOfRotation/z',
                              self._ui.centerOfRotationZ.text(), self.tr("Center of Rotation Z"))
                db.setValue(self._xpath + '/region', self._region, self.tr('Region'))
                db.setValue(self._xpath + '/boundaries',
                              ' '.join(str(bcid) for bcid in self._boundaries), self.tr("Boundaries"))

                if self._isNew:
                    db.setValue(self._xpath + '/name', name, self.tr("Name"))
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

        self._name = name

        super().accept()

    def reject(self):
        super().reject()
        if self._isNew:
            db = coredb.CoreDB()
            db.removeForceMonitor(self._name)

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)
        self._ui.select.clicked.connect(self._selectBoundaries)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(db.getValue(self._xpath + '/writeInterval'))

        self._ui.specificationMethod.setCurrentData(
            DirectionSpecificationMethod(db.getValue(self._xpath + '/forceDirection/specificationMethod')))
        self._ui.dragDirectionX.setText(db.getValue(self._xpath + '/forceDirection/dragDirection/x'))
        self._ui.dragDirectionY.setText(db.getValue(self._xpath + '/forceDirection/dragDirection/y'))
        self._ui.dragDirectionZ.setText(db.getValue(self._xpath + '/forceDirection/dragDirection/z'))
        self._ui.liftDirectionX.setText(db.getValue(self._xpath + '/forceDirection/liftDirection/x'))
        self._ui.liftDirectionY.setText(db.getValue(self._xpath + '/forceDirection/liftDirection/y'))
        self._ui.liftDirectionZ.setText(db.getValue(self._xpath + '/forceDirection/liftDirection/z'))
        self._ui.AoA.setText(db.getValue(self._xpath + '/forceDirection/angleOfAttack'))
        self._ui.AoS.setText(db.getValue(self._xpath + '/forceDirection/angleOfSideslip'))

        self._ui.centerOfRotationX.setText(db.getValue(self._xpath + '/centerOfRotation/x'))
        self._ui.centerOfRotationY.setText(db.getValue(self._xpath + '/centerOfRotation/y'))
        self._ui.centerOfRotationZ.setText(db.getValue(self._xpath + '/centerOfRotation/z'))
        self._region = db.getValue(self._xpath + '/region')
        boundaries = db.getValue(self._xpath + '/boundaries')
        self._setBoundaries(boundaries.split() if boundaries else [])

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

    def _specificationMethodChanged(self, method):
        if method == DirectionSpecificationMethod.DIRECT:
            self._ui.direction.setTitle(self.tr('Direction'))
            self._ui.angles.hide()
        else:
            self._ui.direction.setTitle(self.tr('Direction at AOA=0, AOS=0'))
            self._ui.angles.show()
