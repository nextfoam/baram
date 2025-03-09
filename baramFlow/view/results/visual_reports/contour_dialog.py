#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

import qasync

from baramFlow.coredb.contour import Contour
from baramFlow.coredb.post_field import Field, FieldType, getAvailableFields
from baramFlow.coredb.visual_reports_db import VisualReportsDB
from baramFlow.coredb.post_field import FIELD_TEXTS
from widgets.async_message_box import AsyncMessageBox
from widgets.time_slider import TimeSlider

from .contour_dialog_ui import Ui_ContourDialog


class ContourDialog(QDialog):
    def __init__(self, parent, contour: Contour, times: list[str]):
        super().__init__(parent)

        self._ui = Ui_ContourDialog()
        self._ui.setupUi(self)

        self._timeSlider = TimeSlider(self._ui.slider, self._ui.currentTime, self._ui.lastTime)
        self._timeSlider.updateTimeValues(times)
        self._timeSlider.setCurrentTime(contour.time)

        self._fields: list[Field] = getAvailableFields()
        for f in self._fields:
            if f in FIELD_TEXTS:
                self._ui.field.addItem(FIELD_TEXTS[f], f)
            else:
                self._ui.field.addItem(f.codeName, f)

        # Set Configured Field into combobox
        index = self._ui.field.findData(contour.field)
        self._ui.field.setCurrentIndex(index)

        if contour.field.type == FieldType.VECTOR:
            self._ui.vectorComponent.setEnabled(True)
            index = self._ui.vectorComponent.findData(contour.vectorComponent)
            self._ui.vectorComponent.setCurrentIndex(index)
        else:
            self._ui.vectorComponent.setEnabled(False)

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))

        self._ui.name.setText(contour.name)

        index = self._ui.field.findData(contour.field)
        self._ui.field.setCurrentIndex(index)

        self._contour = contour

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.field.currentIndexChanged.connect(self._fieldChanged)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._contour.name = self._ui.name.text()
        self._contour.field = self._ui.field.currentData()
        self._contour.vectorComponent = self._ui.vectorComponent.currentData()

        self._contour.time = self._timeSlider.getCurrentTime()

        super().accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        super().reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if VisualReportsDB().nameDuplicates(self._contour.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Contour Name already exists.'))
            return False

        return True

    def _fieldChanged(self, index):
        field: Field = self._ui.field.currentData()

        if field.type == FieldType.VECTOR:
            self._ui.vectorComponent.setEnabled(True)
        else:
            self._ui.vectorComponent.setEnabled(False)
