#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

import qasync

from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.models_db import ModelsDB, MultiphaseModel
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.run_calculation_db import TimeSteppingMethod, DataWriteFormat, RunCalculationDB
from baramFlow.view.widgets.content_page import ContentPage
from widgets.async_message_box import AsyncMessageBox
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

        self._ui.timeSteppingMethod.addItem(self.tr('Fixed'), TimeSteppingMethod.FIXED)
        self._ui.timeSteppingMethod.addItem(self.tr('Adaptive'), TimeSteppingMethod.ADAPTIVE)

        self._ui.dataWriteFormat.addItem(self.tr('Binary'), DataWriteFormat.BINARY)
        self._ui.dataWriteFormat.addItem(self.tr('ASCII'), DataWriteFormat.ASCII)

        self._xpath = RunCalculationDB.RUN_CALCULATION_XPATH + '/runConditions'

        self._connectSignalsSlots()

    def _load(self):
        db = coredb.CoreDB()

        isTimeTransient = GeneralDB.isTimeTransient()
        if isTimeTransient:
            if GeneralDB.isCompressibleDensity():
                self._ui.timeSteppingMethod.setEnabled(False)
                method = TimeSteppingMethod.FIXED
            else:
                method = TimeSteppingMethod(db.getValue(self._xpath + '/timeSteppingMethod'))

            index = self._ui.timeSteppingMethod.findData(method)
            self._ui.timeSteppingMethod.setCurrentIndex(index)

            self._ui.iterationConditionsLayout.setRowVisible(self._ui.numberOfIterations, False)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeSteppingMethod, True)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.endTime, True)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxDi, RegionDB.isMultiRegion())

            self._updateVisibleStateOfIterationConditionsLayout(method)

            self._ui.steadyReportInterval.setVisible(False)
            self._ui.transientReportInterval.setVisible(True)
        else:
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.numberOfIterations, True)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeSteppingMethod, False)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeStepSize, False)
            self._ui.iterationConditionsLayout.setRowVisible(
                self._ui.maxCourantNumber,
                GeneralDB.isCompressibleDensity() or ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxDi, False)
            self._ui.iterationConditionsLayout.setRowVisible(
                self._ui.maxCourantNumberForVoF,
                ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.endTime, False)
            self._ui.steadyReportInterval.setVisible(True)
            self._ui.transientReportInterval.setVisible(False)

        self._ui.numberOfIterations.setText(db.getValue(self._xpath + '/numberOfIterations'))
        self._ui.maxCourantNumber.setText(db.getValue(self._xpath + '/maxCourantNumber'))
        self._ui.maxCourantNumberForVoF.setText(db.getValue(self._xpath + '/VoFMaxCourantNumber'))
        self._ui.maxDi.setText(db.getValue(self._xpath + '/maxDiffusionNumber'))
        self._ui.timeStepSize.setText(db.getValue(self._xpath + '/timeStepSize'))
        self._ui.endTime.setText(db.getValue(self._xpath + '/endTime'))

        self._ui.reportIntervalIterationSteps.setText(
            db.getValue(self._xpath + '/reportIntervalSteps'))
        self._ui.reportIntervalSeconds.setText(db.getValue(self._xpath + '/reportIntervalSeconds'))
        self._ui.retainOnlyTheMostRecentFiles.setChecked(
            db.getValue(self._xpath + '/retainOnlyTheMostRecentFiles') == 'true')
        self._ui.maximumNumberODataFiles.setText(db.getValue(self._xpath + '/maximumNumberOfDataFiles'))
        self._ui.dataWriteFormat.setCurrentIndex(
            self._ui.dataWriteFormat.findData(DataWriteFormat(db.getValue(self._xpath + '/dataWriteFormat'))))
        self._ui.dataWritePrecision.setText(db.getValue(self._xpath + '/dataWritePrecision'))
        self._ui.timePrecision.setText(db.getValue(self._xpath + '/timePrecision'))

    @qasync.asyncSlot()
    async def save(self):
        try:
            with coredb.CoreDB() as db:
                if GeneralDB.isTimeTransient():
                    timeSteppingMethod = self._ui.timeSteppingMethod.currentData()
                    db.setValue(self._xpath + '/timeSteppingMethod', timeSteppingMethod.value)
                    if timeSteppingMethod == TimeSteppingMethod.FIXED:
                        db.setValue(self._xpath + '/timeStepSize', self._ui.timeStepSize.text(),
                                    self.tr('Time Step Size'))

                    db.setValue(self._xpath + '/endTime', self._ui.endTime.text(), self.tr('End Time'))

                    db.setValue(self._xpath + '/reportIntervalSeconds', self._ui.reportIntervalSeconds.text(),
                                self.tr('Report Interval Seconds'))
                else:
                    db.setValue(self._xpath + '/numberOfIterations', self._ui.numberOfIterations.text(),
                                self.tr('Number of Iteration'))

                    db.setValue(self._xpath + '/reportIntervalSteps', self._ui.reportIntervalIterationSteps.text(),
                                self.tr('Report Interval Interation Steps'))

                db.setValue(self._xpath + '/maxCourantNumber', self._ui.maxCourantNumber.text(),
                            self.tr('Courant Number'))
                db.setValue(self._xpath + '/VoFMaxCourantNumber', self._ui.maxCourantNumberForVoF.text(),
                            self.tr('Courant Number For VoF'))
                db.setValue(self._xpath + '/maxDiffusionNumber', self._ui.maxDi.text(), self.tr('Max Diffusion Number'))

                if self._ui.retainOnlyTheMostRecentFiles.isChecked():
                    db.setValue(self._xpath + '/retainOnlyTheMostRecentFiles', 'true')
                    db.setValue(self._xpath + '/maximumNumberOfDataFiles', self._ui.maximumNumberODataFiles.text(),
                                self.tr('Maximum Number of Data Files'))
                else:
                    db.setValue(self._xpath + '/retainOnlyTheMostRecentFiles', 'false')

                db.setValue(self._xpath + '/dataWriteFormat', self._ui.dataWriteFormat.currentData().value,
                              self.tr('Data Write Format'))
                db.setValue(self._xpath + '/dataWritePrecision', self._ui.dataWritePrecision.text(),
                              self.tr('Data Write Precision'))
                db.setValue(self._xpath + '/timePrecision', self._ui.timePrecision.text(), self.tr('Time Precision'))

                return True
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))
            return False

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.timeSteppingMethod.currentIndexChanged.connect(self._timeSteppingMethodChanged)

    def _timeSteppingMethodChanged(self, index):
        if not GeneralDB.isTimeTransient():
            return

        method = self._ui.timeSteppingMethod.itemData(index)
        self._updateVisibleStateOfIterationConditionsLayout(method)

    def _updateVisibleStateOfIterationConditionsLayout(self, method: TimeSteppingMethod):
        if method == TimeSteppingMethod.FIXED:
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeStepSize, True)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxCourantNumber, False)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxCourantNumberForVoF, False)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxDi, False)
            if GeneralDB.isCompressibleDensity():  # exceptional for TSLAeroFoam
                self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxCourantNumber, True)

        elif method == TimeSteppingMethod.ADAPTIVE:
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.timeStepSize, False)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxCourantNumber, True)
            self._ui.iterationConditionsLayout.setRowVisible(
                self._ui.maxCourantNumberForVoF, ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID)
            self._ui.iterationConditionsLayout.setRowVisible(self._ui.maxDi, RegionDB.isMultiRegion())
