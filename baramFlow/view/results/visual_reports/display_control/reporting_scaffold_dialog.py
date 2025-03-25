#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QDialog
import qasync

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
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    def open(self, displayItem: DisplayItem):
        self._displayItem = displayItem

        self._ui.maxNumberOfSamplingPoints.setText(str(displayItem.scaffold().maxNumberOfSamplePoints))

        self._ui.streamlinesIntegrateForward.setChecked(displayItem.scaffold().streamlinesIntegrateForward)
        self._ui.streamlinesIntegrateBackward.setChecked(displayItem.scaffold().streamlinesIntegrateBackward)

        super().open()

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        maxNumberOfSamplePoints = int(self._ui.maxNumberOfSamplingPoints.text())

        if maxNumberOfSamplePoints != self._displayItem.scaffold().maxNumberOfSamplePoints:
            progressDialog = ProgressDialog(self, self.tr('Updating Graphics'))
            progressDialog.open()

            self._displayItem.scaffold().maxNumberOfSamplePoints = maxNumberOfSamplePoints
            self._displayItem.scaffold().streamlinesIntegrateForward = self._ui.streamlinesIntegrateForward.isChecked()
            self._displayItem.scaffold().streamlinesIntegrateBackward = self._ui.streamlinesIntegrateBackward.isChecked()

            self._displayItem.scaffold().markUpdated()

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
