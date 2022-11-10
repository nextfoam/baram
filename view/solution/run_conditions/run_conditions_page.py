#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from enum import Enum, Flag, auto
from pathlib import Path

from PySide6.QtWidgets import QWidget, QMessageBox, QFormLayout, QFileDialog

from coredb import coredb
from coredb.app_settings import AppSettings
from coredb.coredb_writer import CoreDBWriter
from coredb.general_db import GeneralDB
from coredb.run_calculation_db import TimeSteppingMethod, DataWriteFormat, RunCalculationDB
from .run_conditions_page_ui import Ui_RunConditionsPage


class TimeCondition(Enum):
    TIME_STEPPING_METHOD = 0
    TIME_STEP_SIZE = auto()
    MAX_COURANT_NUMBER = auto()
    END_TIME = auto()


class TimeSteppingMethodFlag(Flag):
    FIXED = auto()
    ADAPTIVE = auto()


class RunConditionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_RunConditionsPage()
        self._ui.setupUi(self)

        self._timeConditionForm = self._ui.timeConditionLayout

        self._timeSteppingMethods = {
            TimeSteppingMethod.FIXED.value: self.tr('Fixed'),
            TimeSteppingMethod.ADAPTIVE.value: self.tr('Adaptive'),
        }

        self._timeSteppingMethodFlags = {
            TimeSteppingMethod.FIXED.value: TimeSteppingMethodFlag.FIXED,
            TimeSteppingMethod.ADAPTIVE.value: TimeSteppingMethodFlag.ADAPTIVE
        }

        self._dataWriteFormats = {
            DataWriteFormat.BINARY.value: self.tr('Binary'),
            DataWriteFormat.ASCII.value: self.tr('ASCII'),
        }

        self._setupCombo(self._ui.timeSteppingMethod, self._timeSteppingMethods)
        self._setupCombo(self._ui.dataWriteFormat, self._dataWriteFormats)

        self._timeConditions = [
            self._getRowWidgets(TimeCondition.TIME_STEP_SIZE.value,
                                TimeSteppingMethodFlag.FIXED),
            self._getRowWidgets(TimeCondition.MAX_COURANT_NUMBER.value,
                                TimeSteppingMethodFlag.ADAPTIVE),
            self._getRowWidgets(TimeCondition.END_TIME.value,
                                TimeSteppingMethodFlag.FIXED | TimeSteppingMethodFlag.ADAPTIVE),
        ]

        self._db = coredb.CoreDB()
        self._xpath = RunCalculationDB.RUN_CALCULATION_XPATH

        self._connectSignalsSlots()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        timeIsTransient = GeneralDB.isTimeTransient()
        self._ui.steadyConditions.setVisible(not timeIsTransient)
        self._ui.transientConditions.setVisible(timeIsTransient)
        self._ui.steadyReportInterval.setVisible(not timeIsTransient)
        self._ui.transientReportInterval.setVisible(timeIsTransient)

        self._ui.numberOfIterations.setText(self._db.getValue(self._xpath + '/runConditions/numberOfIterations'))

        self._ui.timeSteppingMethod.setCurrentText(
            self._timeSteppingMethods[self._db.getValue(self._xpath + '/runConditions/timeSteppingMethod')])
        self._ui.maxCourantNumber.setText(self._db.getValue(self._xpath + '/runConditions/maxCourantNumber'))
        self._ui.timeStepSize.setText(self._db.getValue(self._xpath + '/runConditions/timeStepSize'))
        self._ui.endTime.setText(self._db.getValue(self._xpath + '/runConditions/endTime'))
        self._timeSteppingMethodChanged()

        self._ui.reportIntervalIterationSteps.setText(self._db.getValue(self._xpath + '/runConditions/reportIntervalSteps'))
        self._ui.reportIntervalSeconds.setText(self._db.getValue(self._xpath + '/runConditions/reportIntervalSeconds'))
        self._ui.retainOnlyTheMostRecentFiles.setChecked(
            self._db.getValue(self._xpath + '/runConditions/retainOnlyTheMostRecentFiles') == 'true')
        self._ui.maximumNumberODataFiles.setText(self._db.getValue(self._xpath + '/runConditions/maximumNumberOfDataFiles'))
        self._ui.dataWriteFormat.setCurrentText(
            self._dataWriteFormats[self._db.getValue(self._xpath + '/runConditions/dataWriteFormat')])
        self._ui.dataWritePrecision.setText(self._db.getValue(self._xpath + '/runConditions/dataWritePrecision'))
        self._ui.timePrecision.setText(self._db.getValue(self._xpath + '/runConditions/timePrecision'))

        self._ui.numberOfCores.setText(self._db.getValue(self._xpath + '/parallel/numberOfCores'))
        self._ui.cluster.setChecked(
            self._db.getValue(self._xpath + '/parallel/localhost') == 'false')
        self._ui.hostFile.setText(self._db.getValue(self._xpath + '/parallel/hostfile'))

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if not ev.spontaneous():
            self.save()

        return super().hideEvent(ev)

    def save(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/runConditions/numberOfIterations', self._ui.numberOfIterations.text(),
                      self.tr('Number of Iteration'))

        timeSteppingMethod = self._ui.timeSteppingMethod.currentData()
        writer.append(self._xpath + '/runConditions/timeSteppingMethod', timeSteppingMethod, None)
        if timeSteppingMethod == TimeSteppingMethod.FIXED.value:
            writer.append(self._xpath + '/runConditions/timeStepSize', self._ui.timeStepSize.text(),
                          self.tr('Time Step Size'))
        elif timeSteppingMethod == TimeSteppingMethod.ADAPTIVE.value:
            writer.append(self._xpath + '/runConditions/maxCourantNumber', self._ui.maxCourantNumber.text(),
                          self.tr('Max Courant Number'))
        writer.append(self._xpath + '/runConditions/endTime', self._ui.endTime.text(), self.tr('End Time'))

        writer.append(self._xpath + '/runConditions/reportIntervalSteps', self._ui.reportIntervalIterationSteps.text(),
                      self.tr('Report Interval Interation Steps'))
        writer.append(self._xpath + '/runConditions/reportIntervalSeconds', self._ui.reportIntervalSeconds.text(),
                      self.tr('Report Interval Seconds'))
        writer.append(self._xpath + '/runConditions/retainOnlyTheMostRecentFiles',
                      'true' if self._ui.retainOnlyTheMostRecentFiles.isChecked() else 'false',
                      self.tr('Retain Only the Most Recent Files'))
        writer.append(self._xpath + '/runConditions/maximumNumberOfDataFiles', self._ui.maximumNumberODataFiles.text(),
                      self.tr('Maximum Number of Data Files'))
        writer.append(self._xpath + '/runConditions/dataWriteFormat', self._ui.dataWriteFormat.currentData(),
                      self.tr('Data Write Format'))
        writer.append(self._xpath + '/runConditions/dataWritePrecision', self._ui.dataWritePrecision.text(),
                      self.tr('Data Write Precision'))
        writer.append(self._xpath + '/runConditions/timePrecision', self._ui.timePrecision.text(),
                      self.tr('Time Precision'))

        writer.append(self._xpath + '/parallel/numberOfCores', self._ui.numberOfCores.text(),
                      self.tr('Number of Cores'))
        writer.append(self._xpath + '/parallel/localhost',
                      'false' if self._ui.cluster.isChecked() else 'true',
                      self.tr('Cluster'))
        writer.append(self._xpath + '/parallel/hostfile', self._ui.hostFile.text(), None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
            return False

        return True

    def _connectSignalsSlots(self):
        self._ui.timeSteppingMethod.currentIndexChanged.connect(self._timeSteppingMethodChanged)
        self._ui.selectHostFile.clicked.connect(self._selectHostFileClicked)

    def _setupCombo(self, combo, items):
        for value, text in items.items():
            combo.addItem(text, value)

    def _getRowWidgets(self, row, flag):
        return (flag,
                self._timeConditionForm.itemAt(row, QFormLayout.LabelRole).widget(),
                self._timeConditionForm.itemAt(row, QFormLayout.FieldRole).widget())

    def _timeSteppingMethodChanged(self):
        rowCount = self._timeConditionForm.rowCount()
        removeIndex = TimeCondition.TIME_STEP_SIZE.value
        for _ in range(1, rowCount):
            labelItem = self._timeConditionForm.itemAt(removeIndex, QFormLayout.LabelRole)
            fieldItem = self._timeConditionForm.itemAt(removeIndex, QFormLayout.FieldRole)
            label = labelItem.widget()
            field = fieldItem.widget()
            self._timeConditionForm.removeItem(labelItem)
            self._timeConditionForm.removeItem(fieldItem)
            self._timeConditionForm.removeRow(removeIndex)
            label.setParent(None)
            field.setParent(None)

        flag = self._timeSteppingMethodFlags[self._ui.timeSteppingMethod.currentData()]
        for c in self._timeConditions:
            if c[0] & flag:
                self._timeConditionForm.addRow(c[1], c[2])

    def _selectHostFileClicked(self, widget):
        _locationParent = Path(AppSettings.getRecentLocation()).resolve()

        self._dialogHostFile = QFileDialog(self, self.tr('Select host file'), str(_locationParent), 'All Files (*.*)')
        self._dialogHostFile.setFileMode(QFileDialog.FileMode.ExistingFile)
        self._dialogHostFile.accepted.connect(self._acceptedHostFile)
        self._dialogHostFile.open()

    def _acceptedHostFile(self):
        if files := self._dialogHostFile.selectedFiles():
            self._ui.hostFile.setText(path.basename(files[0]))

        # Project.instance().fileDB().putHostFile()

