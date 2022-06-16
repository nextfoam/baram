#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from .initialization_page_ui import Ui_InitializationPage
from .option_dialog import OptionDialog


class OptionType(Enum):
    OFF = auto()
    SET_FIELDS = auto()
    MAP_FIELDS = auto()
    POTENTIAL_FLOW = auto()


class InitializationPage(QWidget):
    INITIALIZATION_XPATH = './/initialization'

    def __init__(self):
        super().__init__()
        self._ui = Ui_InitializationPage()
        self._ui.setupUi(self)

        self._ui.optionRadioGroup.setId(self._ui.off, OptionType.OFF.value)
        self._ui.optionRadioGroup.setId(self._ui.setFields, OptionType.SET_FIELDS.value)
        self._ui.optionRadioGroup.setId(self._ui.mapFields, OptionType.MAP_FIELDS.value)
        self._ui.optionRadioGroup.setId(self._ui.potentialFlow, OptionType.POTENTIAL_FLOW.value)

        self._db = coredb.CoreDB()
        self._xpath = self.INITIALIZATION_XPATH
        self._dialog = None

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.create.clicked.connect(self._createOption)
        self._ui.delete_.clicked.connect(self._deleteOption)
        self._ui.display.clicked.connect(self._displayOption)
        self._ui.edit.clicked.connect(self._editOption)
        self._ui.selectSourceCase.clicked.connect(self._selectSourceCase)
        self._ui.initialize.clicked.connect(self._initialize)

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._ui.xVelocity.setText(self._db.getValue(self._xpath + '/initialValues/velocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(self._xpath + '/initialValues/velocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(self._xpath + '/initialValues/velocity/z'))
        self._ui.pressure.setText(self._db.getValue(self._xpath + '/initialValues/pressure'))
        self._ui.temperature.setText(self._db.getValue(self._xpath + '/initialValues/temperature'))
        self._ui.scaleOfVelocity.setText(self._db.getValue(self._xpath + '/initialValues/scaleOfVelocity'))
        self._ui.turbulentIntensity.setText(self._db.getValue(self._xpath + '/initialValues/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(self._db.getValue(self._xpath + '/initialValues/turbulentViscosity'))

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if ev.spontaneous():
            return super().hideEvent(ev)

        writer = CoreDBWriter()
        writer.append(self._xpath + '/initialValues/velocity/x', self._ui.xVelocity.text(), self.tr("X-Velocity"))
        writer.append(self._xpath + '/initialValues/velocity/y', self._ui.yVelocity.text(), self.tr("Y-Velocity"))
        writer.append(self._xpath + '/initialValues/velocity/z', self._ui.zVelocity.text(), self.tr("Z-Velocity"))
        writer.append(self._xpath + '/initialValues/pressure', self._ui.pressure.text(), self.tr("Pressure"))
        writer.append(self._xpath + '/initialValues/temperature', self._ui.temperature.text(), self.tr("Temperature"))
        writer.append(self._xpath + '/initialValues/scaleOfVelocity',
                      self._ui.scaleOfVelocity.text(), self.tr("Scale of Velocity"))
        writer.append(self._xpath + '/initialValues/turbulentIntensity',
                      self._ui.turbulentIntensity.text(), self.tr("Turbulent Intensity"))
        writer.append(self._xpath + '/initialValues/turbulentViscosity',
                      self._ui.turbulentViscosityRatio.text(), self.tr("Turbulent Viscosity"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())

        return super().hideEvent(ev)

    def _createOption(self):
        self._dialog = OptionDialog()
        self._dialog.open()

    def _deleteOption(self):
        pass

    def _displayOption(self):
        pass

    def _editOption(self):
        self._dialog = OptionDialog()
        self._dialog.open()

    def _selectSourceCase(self):
        directoryName = QFileDialog.getExistingDirectory(self, self.tr("Folder Selection"))

    def _initialize(self):
        confirm = QMessageBox.question(self, self.tr("Initialize"), self.tr("All saved data will be deleted. OK?"))
        if confirm == QMessageBox.Yes:
            pass
