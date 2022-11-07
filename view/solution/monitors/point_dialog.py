#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.boundary_db import BoundaryDB
from coredb.monitor_db import MonitorDB, FieldHelper
from view.widgets.selector_dialog import SelectorDialog
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

        self._setupFieldCombo(FieldHelper.getAvailableFields())

        self._name = name
        self._isNew = False
        self._db = coredb.CoreDB()

        if name is None:
            self._name = self._db.addPointMonitor()
            self._isNew = True
        else:
            self._ui.nameWidget.hide()
            self._ui.groupBox.setTitle(name)

        self._xpath = MonitorDB.getPointMonitorXPath(self._name)
        self._snapOntoBoundary = None

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

        writer = CoreDBWriter()
        field = self._ui.field.currentData()
        writer.append(self._xpath + '/writeInterval', self._ui.writeInterval.text(), self.tr("Write Interval"))
        writer.append(self._xpath + '/field/field', field.field, None)
        writer.append(self._xpath + '/field/mid', field.mid, None)
        writer.append(self._xpath + '/coordinate/x', self._ui.coordinateX.text(), self.tr("Coordinate X"))
        writer.append(self._xpath + '/coordinate/y', self._ui.coordinateY.text(), self.tr("Coordinate Y"))
        writer.append(self._xpath + '/coordinate/z', self._ui.coordinateZ.text(), self.tr("Coordinate Z"))
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
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            if self._isNew:
                self._name = name

            super().accept()

    def reject(self):
        super().reject()
        if self._isNew:
            self._db.removePointMonitor(self._name)

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSnapOntoBoundary)

    def _load(self):
        self._ui.name.setText(self._name)
        self._ui.writeInterval.setText(self._db.getValue(self._xpath + '/writeInterval'))
        self._ui.field.setCurrentText(
            FieldHelper.DBFieldKeyToText(self._db.getValue(self._xpath + '/field/field'),
                                         self._db.getValue(self._xpath + '/field/mid')))
        self._ui.coordinateX.setText(self._db.getValue(self._xpath + '/coordinate/x'))
        self._ui.coordinateY.setText(self._db.getValue(self._xpath + '/coordinate/y'))
        self._ui.coordinateZ.setText(self._db.getValue(self._xpath + '/coordinate/z'))
        snapOntoBoundary = self._db.getValue(self._xpath + '/snapOntoBoundary')
        if snapOntoBoundary == 'true':
            self._setSnapOntoBoundary(self._db.getValue(self._xpath + '/boundary'))
        else:
            self._setSnapOntoBoundary(None)

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
