#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional
from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QMessageBox, QPushButton, QHBoxLayout
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from resources import resource
from widgets.flat_push_button import FlatPushButton

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel, TurbulenceModelsDB, RANSModel
from baramFlow.coredb.region_db import RegionDB
from baramFlow.mesh.vtk_loader import hexActor, cylinderActor, sphereActor
from baramFlow.view.widgets.species_widget import SpeciesWidget
from baramFlow.view.widgets.user_defined_scalars_widget import UserDefinedScalarsWidget
from baramFlow.view.widgets.volume_fraction_widget import VolumeFractionWidget
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
    eyeToggled = Signal(bool)

    def __init__(self, name, rname):
        super().__init__()

        self._name = name
        self._rname = rname
        self._key = f'{rname}:{name}'
        self._actor = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._eye = QPushButton(self)
        self._eyeOn: bool = False
        self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-off-outline.svg'))))
        self._eye.setFlat(True)
        self._eye.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._eye.clicked.connect(self.onClicked)

        layout.addWidget(self._eye)

        self._button = FlatPushButton(self)
        self._button.setStyleSheet('text-align: left;')
        self._button.setText(name)
        self._button.setCheckable(True)
        self._button.toggled.connect(self.toggled)
        self._button.doubleClicked.connect(self.doubleClicked)
        self._button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(self._button)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self._button.setText(value)

    @property
    def key(self):
        return f'{self._rname}:{self._name}'

    def actor(self):
        if self._actor is None:
            db = coredb.CoreDB()
            xpath = f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{self._name}"]'

            typeString = db.getValue(xpath + '/type')
            if typeString == 'hex':
                self._actor = hexActor(db.getVector(xpath + '/point1'), db.getVector(xpath + '/point2'))
            elif typeString == 'cylinder':
                self._actor = cylinderActor(db.getVector(xpath + '/point1'),
                                            db.getVector(xpath + '/point2'),
                                            float(db.getValue(xpath + '/radius')))
            elif typeString == 'sphere':
                self._actor = sphereActor(db.getVector(xpath + '/point1'), float(db.getValue(xpath + '/radius')))
            elif typeString == 'cellZone':
                self._actor = app.cellZoneActor(int(db.getValue(xpath + '/cellZone')))

        return self._actor

    def isDisplayOn(self):
        return self._eyeOn

    def onClicked(self, checked):
        if self._eyeOn:
            self.displayOff()
        else:
            self.displayOn()

        self.eyeToggled.emit(self._eyeOn)

    def check(self):
        self._button.setChecked(True)

    def uncheck(self):
        self._button.setChecked(False)

    def displayOn(self):
        self._eyeOn = True
        self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-outline.svg'))))

    def displayOff(self):
        self._eyeOn = False
        self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-off-outline.svg'))))

    def removeActor(self):
        self._actor = None


class InitializationWidget(QWidget):
    displayChecked = Signal(SectionRow)
    displayUnchecked = Signal(SectionRow)

    def __init__(self, rname: str):
        super().__init__()
        self._ui = Ui_initializationWidget()
        self._ui.setupUi(self)

        self._rname = rname
        self._initialValuesPath = f'regions/region[name="{rname}"]/initialization/initialValues'
        self._dialog = None
        self._sectionDialog: Optional[SectionDialog] = None
        self._rows = {}
        self._currentRow: Optional[SectionRow] = None

        self._volumeFractionWidget = VolumeFractionWidget(rname)
        self._scalarsWidget = UserDefinedScalarsWidget(rname)
        self._speciesWidget = SpeciesWidget(RegionDB.getMaterial(self._rname))

        if self._volumeFractionWidget.on():
            self._ui.initialValuesLayout.addWidget(self._volumeFractionWidget)

        if self._scalarsWidget.on():
            self._ui.initialValuesLayout.addWidget(self._scalarsWidget)

        if self._speciesWidget.on():
            self._ui.initialValuesLayout.addWidget(self._speciesWidget)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.create.clicked.connect(self._createOption)
        self._ui.delete_.clicked.connect(self._deleteOption)
        self._ui.edit.clicked.connect(self._editOption)

    def load(self):
        db = coredb.CoreDB()

        self._ui.xVelocity.setText(db.getValue(self._initialValuesPath + '/velocity/x'))
        self._ui.yVelocity.setText(db.getValue(self._initialValuesPath + '/velocity/y'))
        self._ui.zVelocity.setText(db.getValue(self._initialValuesPath + '/velocity/z'))
        self._ui.pressure.setText(db.getValue(self._initialValuesPath + '/pressure'))
        self._ui.temperature.setText(db.getValue(self._initialValuesPath + '/temperature'))
        self._ui.scaleOfVelocity.setText(db.getValue(self._initialValuesPath + '/scaleOfVelocity'))
        self._ui.turbulentIntensity.setText(db.getValue(self._initialValuesPath + '/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(db.getValue(self._initialValuesPath + '/turbulentViscosity'))

        turbulenceModel = ModelsDB.getTurbulenceModel()
        self._ui.temperature.setEnabled(ModelsDB.isEnergyModelOn())
        self._ui.turbulence.setDisabled(turbulenceModel in (TurbulenceModel.INVISCID, TurbulenceModel.LAMINAR))
        self._ui.turbulentIntensity.setDisabled(
            turbulenceModel == TurbulenceModel.SPALART_ALLMARAS
            or TurbulenceModelsDB.getDESRansModel() == RANSModel.SPALART_ALLMARAS
            or TurbulenceModelsDB.isLESSpalartAllmarasModel()
        )

        self._volumeFractionWidget.load(self._initialValuesPath + '/volumeFractions')
        self._scalarsWidget.load(self._initialValuesPath + '/userDefinedScalars')
        self._speciesWidget.load(f'{self._initialValuesPath}/species')

        sections: [str] = db.getList(f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section/name')
        for name in sections:
            if name in self._rows:
                self._rows[name].displayOff()
            else:
                self._addSectionRow(name)

    async def appendToWriter(self, writer):
        writer.append(self._initialValuesPath + '/velocity/x', self._ui.xVelocity.text(),
                      self.tr('X-Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/velocity/y', self._ui.yVelocity.text(),
                      self.tr('Y-Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/velocity/z', self._ui.zVelocity.text(),
                      self.tr('Z-Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/pressure', self._ui.pressure.text(),
                      self.tr('Pressure of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/temperature', self._ui.temperature.text(),
                      self.tr('Temperature of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/scaleOfVelocity', self._ui.scaleOfVelocity.text(),
                      self.tr('Scale of Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/turbulentIntensity', self._ui.turbulentIntensity.text(),
                      self.tr('Turbulent Intensity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/turbulentViscosity', self._ui.turbulentViscosityRatio.text(),
                      self.tr('Turbulent Viscosity of region [{}]').format(self._rname))

        if not await self._volumeFractionWidget.appendToWriter(writer, self._initialValuesPath + '/volumeFractions'):
            return False

        if not self._scalarsWidget.appendToWriter(writer, self._initialValuesPath + '/userDefinedScalars'):
            return False

        if not await self._speciesWidget.appendToWriter(writer, f'{self._initialValuesPath}/species'):
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
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
            return

        row = self._rows.pop(self._currentRow.name)
        if row.isDisplayOn():
            self.displayUnchecked.emit(row)

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

        if name in self._rows:
            row = self._rows[name]
            self.displayUnchecked.emit(row)
            row.removeActor()
            if row.isDisplayOn():
                self.displayChecked.emit(row)
        else:
            self._addSectionRow(name)

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

    def _rowEyeToggled(self, checked):
        row: SectionRow = self.sender()

        if checked:
            self.displayChecked.emit(row)
        else:
            self.displayUnchecked.emit(row)

    def _addSectionRow(self, name):
        row = SectionRow(name, self._rname)
        self._rows[name] = row
        row.toggled.connect(self._rowSelectionChanged)
        row.doubleClicked.connect(self._rowDoubleClicked)
        row.eyeToggled.connect(self._rowEyeToggled)
        idx = self._ui.sectionListLayout.count() - 1
        self._ui.sectionListLayout.insertWidget(idx, row)
