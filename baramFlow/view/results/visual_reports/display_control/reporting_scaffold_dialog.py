#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QDialog
import qasync

from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.view.results.visual_reports.display_control.display_item import DisplayItem
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from .reporting_scaffold_dialog_ui import Ui_ReportingScaffoldDialog


class ReportingScaffoldDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ReportingScaffoldDialog()
        self._ui.setupUi(self)

        self._ui.maxNumberOfSamplingPoints.setValidator(QIntValidator())

        self._displayItem: DisplayItem = None

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.streamlinesIntegrateForward.clicked.connect(self._forwardStateClicked)
        self._ui.streamlinesIntegrateBackward.clicked.connect(self._backwardStateClicked)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    def open(self, displayItem: DisplayItem):
        self._displayItem = displayItem

        rs = displayItem.reportingScaffold

        self._ui.maxNumberOfSamplingPoints.setText(str(rs.maxNumberOfSamplePoints))

        self._ui.streamlinesIntegrateForward.setChecked(rs.streamlinesIntegrateForward)
        self._ui.streamlinesIntegrateBackward.setChecked(rs.streamlinesIntegrateBackward)

        super().open()

    def _forwardStateClicked(self, checked: bool):
        if not checked:
            if not self._ui.streamlinesIntegrateBackward.isChecked():
                self._ui.streamlinesIntegrateForward.setChecked(True)

    def _backwardStateClicked(self, checked: bool):
        if not checked:
            if not self._ui.streamlinesIntegrateForward.isChecked():
                self._ui.streamlinesIntegrateBackward.setChecked(True)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        maxNumber = int(self._ui.maxNumberOfSamplingPoints.text())
        forward = self._ui.streamlinesIntegrateForward.isChecked()
        backward = self._ui.streamlinesIntegrateBackward.isChecked()

        rs = self._displayItem.reportingScaffold

        if maxNumber != rs.maxNumberOfSamplePoints \
            or forward != rs.streamlinesIntegrateForward \
                or backward != rs.streamlinesIntegrateBackward:
            progressDialog = ProgressDialog(self, self.tr('Updating Graphics'), openDelay=500)
            progressDialog.open()

            rs.maxNumberOfSamplePoints = maxNumber
            rs.streamlinesIntegrateForward = forward
            rs.streamlinesIntegrateBackward = backward

            await rs.markUpdated()

            await self._displayItem.executePipeline()

            progressDialog.close()

        super().accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        super().reject()

    async def _valid(self) -> bool:
        maxNumberOfSamplingPoints = int(self._ui.maxNumberOfSamplingPoints.text())
        if maxNumberOfSamplingPoints <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Max. Number of Sample points should be greater than 0.'))
            return False

        return True
