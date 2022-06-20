#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.setup.boundary_conditions.boundary_db import BoundaryDB
from view.widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem
from .force_dialog_ui import Ui_ForceDialog
from .monitor_db import MonitorDB


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
        self._isNew = False
        self._db = coredb.CoreDB()

        if name is None:
            self._name = self._db.addForceMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.groupBox.setTitle(name)

        self._xpath = MonitorDB.getForceMonitorXPath(self._name)
        self._boundaries = None

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
        writer.append(self._xpath + '/referenceArea', self._ui.referenceArea.text(), self.tr("Reference Area"))
        writer.append(self._xpath + '/referenceLength', self._ui.referenceLength.text(), self.tr("Reference Length"))
        writer.append(self._xpath + '/referenceVelocity', self._ui.referenceVelocity.text(), self.tr("Reference Velocity"))
        writer.append(self._xpath + '/referenceDensity', self._ui.referenceDensity.text(), self.tr("Reference Density"))
        writer.append(self._xpath + '/dragDirection/x', self._ui.dragDirectionX.text(), self.tr("Drag Direction X"))
        writer.append(self._xpath + '/dragDirection/y', self._ui.dragDirectionY.text(), self.tr("Drag Direction Y"))
        writer.append(self._xpath + '/dragDirection/z', self._ui.dragDirectionZ.text(), self.tr("Drag Direction Z"))
        writer.append(self._xpath + '/liftDirection/x', self._ui.liftDirectionX.text(), self.tr("Lift Direction X"))
        writer.append(self._xpath + '/liftDirection/y', self._ui.liftDirectionY.text(), self.tr("Lift Direction Y"))
        writer.append(self._xpath + '/liftDirection/z', self._ui.liftDirectionZ.text(), self.tr("Lift Direction Z"))
        writer.append(self._xpath + '/pitchAxisDirection/x', self._ui.pitchAxisDirectionX.text(), self.tr("Pitch Axis Direction X"))
        writer.append(self._xpath + '/pitchAxisDirection/y', self._ui.pitchAxisDirectionY.text(), self.tr("Pitch Axis Direction Y"))
        writer.append(self._xpath + '/pitchAxisDirection/z', self._ui.pitchAxisDirectionZ.text(), self.tr("Pitch Axis Direction Z"))
        writer.append(self._xpath + '/centerOfRotation/x', self._ui.centerOfRotationX.text(), self.tr("Center of Rotation X"))
        writer.append(self._xpath + '/centerOfRotation/y', self._ui.centerOfRotationY.text(), self.tr("Center of Rotation Y"))
        writer.append(self._xpath + '/centerOfRotation/z', self._ui.centerOfRotationZ.text(), self.tr("Center of Rotation Z"))
        writer.append(self._xpath + '/boundaries', ' '.join(b for b in self._boundaries), self.tr("Boundaries"))

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
            self._db.removeForceMonitor(self._name)

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectBoundaries)

    def _load(self):
        self._ui.name.setText(self._name)
        self._ui.referenceArea.setText(self._db.getValue(self._xpath + '/referenceArea'))
        self._ui.referenceLength.setText(self._db.getValue(self._xpath + '/referenceLength'))
        self._ui.referenceVelocity.setText(self._db.getValue(self._xpath + '/referenceVelocity'))
        self._ui.referenceDensity.setText(self._db.getValue(self._xpath + '/referenceDensity'))
        self._ui.dragDirectionX.setText(self._db.getValue(self._xpath + '/dragDirection/x'))
        self._ui.dragDirectionY.setText(self._db.getValue(self._xpath + '/dragDirection/y'))
        self._ui.dragDirectionZ.setText(self._db.getValue(self._xpath + '/dragDirection/z'))
        self._ui.liftDirectionX.setText(self._db.getValue(self._xpath + '/liftDirection/x'))
        self._ui.liftDirectionY.setText(self._db.getValue(self._xpath + '/liftDirection/y'))
        self._ui.liftDirectionZ.setText(self._db.getValue(self._xpath + '/liftDirection/z'))
        self._ui.pitchAxisDirectionX.setText(self._db.getValue(self._xpath + '/pitchAxisDirection/x'))
        self._ui.pitchAxisDirectionY.setText(self._db.getValue(self._xpath + '/pitchAxisDirection/y'))
        self._ui.pitchAxisDirectionZ.setText(self._db.getValue(self._xpath + '/pitchAxisDirection/z'))
        self._ui.centerOfRotationX.setText(self._db.getValue(self._xpath + '/centerOfRotation/x'))
        self._ui.centerOfRotationY.setText(self._db.getValue(self._xpath + '/centerOfRotation/y'))
        self._ui.centerOfRotationZ.setText(self._db.getValue(self._xpath + '/centerOfRotation/z'))
        boundaries = self._db.getValue(self._xpath + '/boundaries')
        self._setBoundaries(boundaries.split() if boundaries else [])

    def _setBoundaries(self, boundaries):
        self._boundaries = boundaries

        self._ui.boundaries.clear()
        for b in boundaries:
            self._ui.boundaries.addItem(f'{BoundaryDB.getBoundaryName(b)} / {BoundaryDB.getBoundaryRegion(b)}')

    def _selectBoundaries(self):
        self._dialog = MultiSelectorDialog(
            self, self.tr("Select Boundaries"),
            [SelectorItem(b.toText(), b.name, b.id) for b in BoundaryDB.getBoundariesForSelector()], self._boundaries)
        self._dialog.open()
        self._dialog.accepted.connect(self._boundariesChanged)

    def _boundariesChanged(self):
        self._setBoundaries(self._dialog.selectedItems())
