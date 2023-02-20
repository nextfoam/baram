#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional
from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QMessageBox, QPushButton, QHBoxLayout
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.models_db import ModelsDB, TurbulenceModel
from resources import resource
from view.widgets.flat_push_button import FlatPushButton
from view.widgets.volume_fraction_widget import VolumeFractionWidget
from .initialization_widget_ui import Ui_initializationWidget
from .section_dialog import SectionDialog


class OptionType(Enum):
    OFF = auto()
    SET_FIELDS = auto()
    MAP_FIELDS = auto()
    POTENTIAL_FLOW = auto()


class SectionRow(QWidget):
    doubleClicked = Signal()
    toggled = Signal(bool)

    def __init__(self, name):
        super().__init__()

        self._name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._eye = QPushButton(self)
        self._eyeOn: bool = False
        self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-off-outline.svg'))))
        self._eye.setFlat(True)
        self._eye.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._eye.clicked.connect(self.onClicked)

        layout.addWidget(self._eye)

        self._button = FlatPushButton(self)
        self._button.setStyleSheet('text-align: left;')
        self._button.setText(name)
        self._button.setCheckable(True)
        self._button.toggled.connect(self.toggled)
        self._button.doubleClicked.connect(self.doubleClicked)
        self._button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout.addWidget(self._button)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self._button.setText(value)

    def onClicked(self, checked):
        if self._eyeOn:
            self._eyeOn = False
            self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-off-outline.svg'))))
        else:
            self._eyeOn = True
            self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-outline.svg'))))

    def check(self):
        self._button.setChecked(True)

    def uncheck(self):
        self._button.setChecked(False)


class InitializationWidget(QWidget):
    def __init__(self, rname: str):
        super().__init__()
        self._ui = Ui_initializationWidget()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._rname = rname
        self._initialValuesPath = f'.//regions/region[name="{rname}"]/initialization/initialValues'
        self._dialog = None
        self._sectionDialog: Optional[SectionDialog] = None
        self._rows = {}
        self._currentRow: Optional[SectionRow] = None

        self._volumeFractionWidget = VolumeFractionWidget(rname, self._initialValuesPath)
        if self._volumeFractionWidget.on():
            self._ui.initialValuesLayout.addWidget(self._volumeFractionWidget)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.create.clicked.connect(self._createOption)
        self._ui.delete_.clicked.connect(self._deleteOption)
        self._ui.edit.clicked.connect(self._editOption)

    def load(self):
        self._ui.xVelocity.setText(self._db.getValue(self._initialValuesPath + '/velocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(self._initialValuesPath + '/velocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(self._initialValuesPath + '/velocity/z'))
        self._ui.pressure.setText(self._db.getValue(self._initialValuesPath + '//pressure'))
        self._ui.temperature.setText(self._db.getValue(self._initialValuesPath + '/temperature'))
        self._ui.scaleOfVelocity.setText(self._db.getValue(self._initialValuesPath + '/scaleOfVelocity'))
        self._ui.turbulentIntensity.setText(self._db.getValue(self._initialValuesPath + '/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(self._db.getValue(self._initialValuesPath + '/turbulentViscosity'))

        self._ui.temperature.setEnabled(ModelsDB.isEnergyModelOn())
        self._ui.turbulence.setEnabled(
            ModelsDB.getTurbulenceModel() not in (TurbulenceModel.INVISCID, TurbulenceModel.LAMINAR))

        if self._volumeFractionWidget.on():
            self._volumeFractionWidget.load()

        sections: [str] = self._db.getList(f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section/name')
        for name in sections:
            if name not in self._rows:
                row = SectionRow(name)
                self._rows[name] = row
                row.toggled.connect(self._rowSelectionChanged)
                row.doubleClicked.connect(self._rowDoubleClicked)
                idx = self._ui.sectionListLayout.count() - 1
                self._ui.sectionListLayout.insertWidget(idx, row)

    def save(self):
        writer = CoreDBWriter()
        writer.append(self._initialValuesPath + '/velocity/x', self._ui.xVelocity.text(), self.tr("X-Velocity"))
        writer.append(self._initialValuesPath + '/velocity/y', self._ui.yVelocity.text(), self.tr("Y-Velocity"))
        writer.append(self._initialValuesPath + '/velocity/z', self._ui.zVelocity.text(), self.tr("Z-Velocity"))
        writer.append(self._initialValuesPath + '/pressure', self._ui.pressure.text(), self.tr("Pressure"))
        writer.append(self._initialValuesPath + '/temperature', self._ui.temperature.text(), self.tr("Temperature"))
        writer.append(self._initialValuesPath + '/scaleOfVelocity',
                      self._ui.scaleOfVelocity.text(), self.tr("Scale of Velocity"))
        writer.append(self._initialValuesPath + '/turbulentIntensity',
                      self._ui.turbulentIntensity.text(), self.tr("Turbulent Intensity"))
        writer.append(self._initialValuesPath + '/turbulentViscosity',
                      self._ui.turbulentViscosityRatio.text(), self.tr("Turbulent Viscosity"))

        if not self._volumeFractionWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
            return False

        return True

    def _createOption(self):
        self._sectionDialog = SectionDialog(self, self._rname)
        self._sectionDialog.accepted.connect(self._updateSectionList)
        self._sectionDialog.open()

    def _deleteOption(self):
        if self._currentRow is None:
            QMessageBox.warning(self, self.tr('Warning'), self.tr('Please select a section to edit'))
            return

        button = QMessageBox.question(self, self.tr('Alert'), self.tr('Delete selected section?'))
        if button == QMessageBox.StandardButton.No:
            return

        sectionPath = f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{self._currentRow.name}"]'

        writer = CoreDBWriter()
        writer.removeElement(sectionPath)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
            return

        del self._rows[self._currentRow.name]
        self._ui.sectionListLayout.removeWidget(self._currentRow)
        self._currentRow.close()
        self._currentRow = None

    def _editOption(self):
        if self._currentRow is None:
            QMessageBox.warning(self, self.tr('Warning'), self.tr('Please select a section to edit'))
            return

        self._sectionDialog = SectionDialog(self, self._rname, self._currentRow.name)
        self._sectionDialog.accepted.connect(self._updateSectionList)
        self._sectionDialog.open()

    def _updateSectionList(self):
        if self._sectionDialog is None:
            return

        name = self._sectionDialog.sectionName

        if name not in self._rows:
            row = SectionRow(name)
            self._rows[name] = row
            row.toggled.connect(self._rowSelectionChanged)
            row.doubleClicked.connect(self._rowDoubleClicked)
            idx = self._ui.sectionListLayout.count() - 1
            self._ui.sectionListLayout.insertWidget(idx, row)

        self._sectionDialog = None

    def _rowSelectionChanged(self, checked):
        row: SectionRow = self.sender()
        if checked:
            self._currentRow = row
            for r in self._rows.values():
                if r != row:
                    r.uncheck()
        else:
            if row == self._currentRow:
                row.check()

    def _rowDoubleClicked(self):
        row: SectionRow = self.sender()
        self._currentRow = row
        for r in self._rows.values():
            if r != row:
                r.uncheck()

        self._editOption()

