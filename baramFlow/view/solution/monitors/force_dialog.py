#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.monitor_db import MonitorDB, DirectionSpecificationMethod
from baramFlow.view.widgets.region_objects_selector import BoundariesSelector

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
            self._ui.groupBox.setTitle(name)

        self._xpath = MonitorDB.getForceMonitorXPath(self._name)

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

        if not self._boundaries:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr("Select Boundaries."))
            return

        writer = CoreDBWriter()
        writer.append(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))

        specificationMethod = self._ui.specificationMethod.currentData()
        writer.append(self._xpath + '/forceDirection/specificationMethod', specificationMethod.value, None)
        writer.append(self._xpath + '/forceDirection/dragDirection/x', self._ui.dragDirectionX.text(),
                      self.tr('Drag Direction'))
        writer.append(self._xpath + '/forceDirection/dragDirection/y', self._ui.dragDirectionY.text(),
                      self.tr('Drag Direction'))
        writer.append(self._xpath + '/forceDirection/dragDirection/z', self._ui.dragDirectionZ.text(),
                      self.tr('Drag Direction'))
        writer.append(self._xpath + '/forceDirection/liftDirection/x', self._ui.liftDirectionX.text(),
                      self.tr('Lift Direction'))
        writer.append(self._xpath + '/forceDirection/liftDirection/y', self._ui.liftDirectionY.text(),
                      self.tr('Lift Direction'))
        writer.append(self._xpath + '/forceDirection/liftDirection/z', self._ui.liftDirectionZ.text(),
                      self.tr('Lift Direction'))
        writer.append(self._xpath + '/forceDirection/angleOfAttack', self._ui.AoA.text(), self.tr('Angle of Attack'))
        writer.append(self._xpath + '/forceDirection/angleOfSideslip', self._ui.AoS.text(), self.tr('Angle of Sideslip'))
        if specificationMethod == DirectionSpecificationMethod.AOA_AOS:
            writer.append(self._xpath + '/forceDirection/angleOfAttack', self._ui.AoA.text(), self.tr('Angle of Attack'))
            writer.append(self._xpath + '/forceDirection/angleOfSideslip', self._ui.AoS.text(),
                          self.tr('Angle of Sideslip'))

        writer.append(self._xpath + '/centerOfRotation/x',
                      self._ui.centerOfRotationX.text(), self.tr("Center of Rotation X"))
        writer.append(self._xpath + '/centerOfRotation/y',
                      self._ui.centerOfRotationY.text(), self.tr("Center of Rotation Y"))
        writer.append(self._xpath + '/centerOfRotation/z',
                      self._ui.centerOfRotationZ.text(), self.tr("Center of Rotation Z"))
        writer.append(self._xpath + '/region', self._region, self.tr('Region'))
        writer.append(self._xpath + '/boundaries',
                      ' '.join(str(bcid) for bcid in self._boundaries), self.tr("Boundaries"))

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
            db = coredb.CoreDB()
            db.removeForceMonitor(self._name)

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)
        self._ui.select.clicked.connect(self._selectBoundaries)

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
