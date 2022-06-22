#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.setup.general.general_db import GeneralDB
from .run_calculation_page_ui import Ui_RunCalculationPage
from .run_calculation_db import TimeSteppingMethod, DataWriteFormat, MachineType, RunCalculationDB


class RunCalculationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_RunCalculationPage()
        self._ui.setupUi(self)

        self._timeSteppingMethods = {
            TimeSteppingMethod.FIXED.value: self.tr("Fixed"),
            TimeSteppingMethod.ADAPTIVE.value: self.tr("Adaptive"),
        }

        self._dataWriteFormats = {
            DataWriteFormat.BINARY.value: self.tr("Binary"),
            DataWriteFormat.ASCII.value: self.tr("ASCII"),
        }

        self._machineTypes = {
            MachineType.SHARED_MEMORY_ON_LOCAL_MACHINE.value: self.tr("Shared Memory on Local Machine, SMP"),
            MachineType.DISTRIBUTED_MEMORY_ON_A_CLUSTER.value: self.tr("Distributed Memory on a Cluster"),
        }

        self._setupCombo(self._ui.timeSteppingMethod, self._timeSteppingMethods)
        self._setupCombo(self._ui.dataWriteFormat, self._dataWriteFormats)
        self._setupCombo(self._ui.machineType, self._machineTypes)

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
        self._ui.timeStepSize.setText(self._db.getValue(self._xpath + '/runConditions/timeStepSize'))
        self._ui.endTime.setText(self._db.getValue(self._xpath + '/runConditions/endTime'))
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
        self._ui.machineType.setCurrentText(
            self._machineTypes[self._db.getValue(self._xpath + '/parallel/machineType')])

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if ev.spontaneous():
            return super().hideEvent(ev)

        writer = CoreDBWriter()
        writer.append(self._xpath + '/runConditions/numberOfIterations', self._ui.numberOfIterations.text(), self.tr("Number of Iteration"))
        writer.append(self._xpath + '/runConditions/timeSteppingMethod', self._ui.timeSteppingMethod.currentData(), None)
        writer.append(self._xpath + '/runConditions/timeStepSize', self._ui.timeStepSize.text(), self.tr("Time Step Size"))
        writer.append(self._xpath + '/runConditions/endTime', self._ui.endTime.text(), self.tr("End Time"))
        writer.append(self._xpath + '/runConditions/reportIntervalSteps', self._ui.reportIntervalIterationSteps.text(), self.tr("Report Interval Interation Steps"))
        writer.append(self._xpath + '/runConditions/reportIntervalSeconds', self._ui.reportIntervalSeconds.text(), self.tr("Report Interval Seconds"))
        writer.append(self._xpath + '/runConditions/retainOnlyTheMostRecentFiles', 'true' if self._ui.retainOnlyTheMostRecentFiles.isChecked() else 'false', self.tr("Report Interval Seconds"))
        writer.append(self._xpath + '/runConditions/maximumNumberOfDataFiles', self._ui.maximumNumberODataFiles.text(), self.tr("Maximum Number of Data Files"))
        writer.append(self._xpath + '/runConditions/dataWriteFormat', self._ui.dataWriteFormat.currentData(), self.tr("Data Write Format"))
        writer.append(self._xpath + '/runConditions/dataWritePrecision', self._ui.dataWritePrecision.text(), self.tr("Data Write Precision"))
        writer.append(self._xpath + '/runConditions/timePrecision', self._ui.timePrecision.text(), self.tr("Time Precision"))

        writer.append(self._xpath + '/parallel/numberOfCores', self._ui.numberOfCores.text(), self.tr("Number of Cores"))
        writer.append(self._xpath + '/parallel/machineType', self._ui.machineType.currentData(), None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())

        return super().hideEvent(ev)

    def _connectSignalsSlots(self):
        pass

    def _setupCombo(self, combo, items):
        for value, text in items.items():
            combo.addItem(text, value)
