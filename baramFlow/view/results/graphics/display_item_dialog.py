#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QDialog
import qasync

from baramFlow.view.results.graphics.display_control import DisplayControl
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from .display_item_dialog_ui import Ui_DisplayItemDialog


class DisplayItemDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_DisplayItemDialog()
        self._ui.setupUi(self)

        self._ui.maxNumberOfSamplingPoints.setValidator(QIntValidator())

        self._displayControl: DisplayControl = None

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.streamlinesIntegrateForward.clicked.connect(self._forwardStateClicked)
        self._ui.streamlinesIntegrateBackward.clicked.connect(self._backwardStateClicked)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    def setDisplayControl(self, displayControl: DisplayControl):
        self._displayControl = displayControl

        item = displayControl.displayItem

        self._ui.maxNumberOfSamplingPoints.setText(str(item.maxNumberOfSamplePoints))

        self._ui.streamlinesIntegrateForward.setChecked(item.streamlinesIntegrateForward)
        self._ui.streamlinesIntegrateBackward.setChecked(item.streamlinesIntegrateBackward)

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

        item = self._displayControl.displayItem

        if maxNumber != item.maxNumberOfSamplePoints \
            or forward != item.streamlinesIntegrateForward \
                or backward != item.streamlinesIntegrateBackward:
            progressDialog = ProgressDialog(self, self.tr('Graphics Parameters'), openDelay=500)
            progressDialog.setLabelText(self.tr('Updating Graphics...'))
            progressDialog.open()

            item.maxNumberOfSamplePoints = maxNumber
            item.streamlinesIntegrateForward = forward
            item.streamlinesIntegrateBackward = backward

            await item.markUpdated()

            await self._displayControl.executePipeline()

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
