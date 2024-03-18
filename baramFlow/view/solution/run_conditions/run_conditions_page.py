#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

import qasync
from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.run_calculation_db import TimeSteppingMethod, DataWriteFormat, RunCalculationDB
from baramFlow.coredb.models_db import ModelsDB, MultiphaseModel
from baramFlow.view.widgets.content_page import ContentPage
from .run_conditions_page_ui import Ui_RunConditionsPage


class TimeCondition(Enum):
    TIME_STEPPING_METHOD = 0
    TIME_STEP_SIZE = auto()
    MAX_COURANT_NUMBER = auto()
    MAX_COURANT_NUMBER_VOF = auto()
    END_TIME = auto()


class RunConditionsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_RunConditionsPage()
        self._ui.setupUi(self)

        self._ui.timeSteppingMethod.addItems({
            TimeSteppingMethod.FIXED: self.tr('Fixed'),
            TimeSteppingMethod.ADAPTIVE: self.tr('Adaptive')
        })

        self._ui.dataWriteFormat.addItems({
            DataWriteFormat.BINARY: self.tr('Binary'),
            DataWriteFormat.ASCII: self.tr('ASCII'),
        })

        self._xpath = RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions'

        self._connectSignalsSlots()

    def _load(self):
        if GeneralDB.isTimeTransient():
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.numberOfIterations, False)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeSteppingMethod, True)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.endTime, True)
            self._ui.steadyReportInterval.setVisible(False)
            self._ui.transientReportInterval.setVisible(True)
        else:
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.numberOfIterations, True)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeSteppingMethod, False)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeStepSize, False)
            self._ui.iterationConditionsLayout.setRowVisible(
                self._ui.maxCourantNumber,
                GeneralDB.isCompressibleDensity() or ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID)
            self._ui.iterationConditionsLayout.setRowVisible(
                self._ui.maxCourantNumberForVoF,
                ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.endTime, False)
            self._ui.steadyReportInterval.setVisible(True)
            self._ui.transientReportInterval.setVisible(False)

        db = coredb.CoreDB()

        self._ui.numberOfIterations.setText(db.getValue(self._xpath + '/numberOfIterations'))

        self._ui.timeSteppingMethod.setCurrentData(TimeSteppingMethod(db.getValue(self._xpath + '/timeSteppingMethod')))
        self._ui.maxCourantNumber.setText(db.getValue(self._xpath + '/maxCourantNumber'))
        self._ui.maxCourantNumberForVoF.setText(db.getValue(self._xpath + '/VoFMaxCourantNumber'))
        self._ui.timeStepSize.setText(db.getValue(self._xpath + '/timeStepSize'))
        self._ui.endTime.setText(db.getValue(self._xpath + '/endTime'))

        self._ui.reportIntervalIterationSteps.setText(
            db.getValue(self._xpath + '/reportIntervalSteps'))
        self._ui.reportIntervalSeconds.setText(db.getValue(self._xpath + '/reportIntervalSeconds'))
        self._ui.retainOnlyTheMostRecentFiles.setChecked(
            db.getValue(self._xpath + '/retainOnlyTheMostRecentFiles') == 'true')
        self._ui.maximumNumberODataFiles.setText(db.getValue(self._xpath + '/maximumNumberOfDataFiles'))
        self._ui.dataWriteFormat.setCurrentData(DataWriteFormat(db.getValue(self._xpath + '/dataWriteFormat')))
        self._ui.dataWritePrecision.setText(db.getValue(self._xpath + '/dataWritePrecision'))
        self._ui.timePrecision.setText(db.getValue(self._xpath + '/timePrecision'))

    @qasync.asyncSlot()
    async def save(self):
        writer = CoreDBWriter()

        if GeneralDB.isTimeTransient():
            timeSteppingMethod = self._ui.timeSteppingMethod.currentData()
            writer.append(self._xpath + '/timeSteppingMethod', timeSteppingMethod.value, None)
            if timeSteppingMethod == TimeSteppingMethod.FIXED:
                writer.append(self._xpath + '/timeStepSize', self._ui.timeStepSize.text(), self.tr('Time Step Size'))

            writer.append(self._xpath + '/endTime', self._ui.endTime.text(), self.tr('End Time'))

            writer.append(self._xpath + '/reportIntervalSeconds', self._ui.reportIntervalSeconds.text(),
                          self.tr('Report Interval Seconds'))
        else:
            writer.append(self._xpath + '/numberOfIterations', self._ui.numberOfIterations.text(),
                          self.tr('Number of Iteration'))

            writer.append(self._xpath + '/reportIntervalSteps',
                          self._ui.reportIntervalIterationSteps.text(), self.tr('Report Interval Interation Steps'))

        writer.append(self._xpath + '/maxCourantNumber', self._ui.maxCourantNumber.text(),
                      self.tr('Courant Number'))
        writer.append(self._xpath + '/VoFMaxCourantNumber',
                      self._ui.maxCourantNumberForVoF.text(), self.tr('Courant Number For VoF'))

        if self._ui.retainOnlyTheMostRecentFiles.isChecked():
            writer.append(self._xpath + '/retainOnlyTheMostRecentFiles', 'true', None)
            writer.append(self._xpath + '/maximumNumberOfDataFiles',
                          self._ui.maximumNumberODataFiles.text(), self.tr('Maximum Number of Data Files'))
        else:
            writer.append(self._xpath + '/retainOnlyTheMostRecentFiles', 'false', None)

        writer.append(self._xpath + '/dataWriteFormat', self._ui.dataWriteFormat.currentValue(),
                      self.tr('Data Write Format'))
        writer.append(self._xpath + '/dataWritePrecision', self._ui.dataWritePrecision.text(),
                      self.tr('Data Write Precision'))
        writer.append(self._xpath + '/timePrecision', self._ui.timePrecision.text(), self.tr('Time Precision'))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
            return False

        return True

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.timeSteppingMethod.currentDataChanged.connect(self._timeSteppingMethodChanged)

    def _timeSteppingMethodChanged(self, method):
        if not GeneralDB.isTimeTransient():
            return

        self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeStepSize, method == TimeSteppingMethod.FIXED)
        self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxCourantNumber,
                                                         method == TimeSteppingMethod.ADAPTIVE)
        self._ui.iterationConditionsLayout.setRowVisible(
            self._ui.maxCourantNumberForVoF,
            method == TimeSteppingMethod.ADAPTIVE and ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID)
