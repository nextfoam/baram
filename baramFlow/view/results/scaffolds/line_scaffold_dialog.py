#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.base.scaffold.line_scaffold import LineScaffold
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB

from widgets.async_message_box import AsyncMessageBox

from .line_scaffold_dialog_ui import Ui_LineScaffoldDialog


class LineScaffoldDialog(QDialog):
    def __init__(self, parent, line: LineScaffold, isNew=False):
        super().__init__(parent)

        self._ui = Ui_LineScaffoldDialog()
        self._ui.setupUi(self)

        self._line = line

        if isNew:
            self._ui.ok.setText('Create')

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))

        self._ui.point1X.setValidator(QDoubleValidator())
        self._ui.point1Y.setValidator(QDoubleValidator())
        self._ui.point1Z.setValidator(QDoubleValidator())

        self._ui.point2X.setValidator(QDoubleValidator())
        self._ui.point2Y.setValidator(QDoubleValidator())
        self._ui.point2Z.setValidator(QDoubleValidator())

        self._ui.numberOfSamples.setValidator(QIntValidator())

        self._ui.name.setText(line.name)

        self._ui.point1X.setText(line.point1X)
        self._ui.point1Y.setText(line.point1Y)
        self._ui.point1Z.setText(line.point1Z)

        self._ui.point2X.setText(line.point2X)
        self._ui.point2Y.setText(line.point2Y)
        self._ui.point2Z.setText(line.point2Z)

        self._ui.numberOfSamples.setText(str(line.numberOfSamples))

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._line.name = self._ui.name.text()

        self._line.point1X = self._ui.point1X.text()
        self._line.point1Y = self._ui.point1Y.text()
        self._line.point1Z = self._ui.point1Z.text()

        self._line.point2X = self._ui.point2X.text()
        self._line.point2Y = self._ui.point2Y.text()
        self._line.point2Z = self._ui.point2Z.text()

        self._line.numberOfSamples = int(self._ui.numberOfSamples.text())

        self.accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        self.reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if ScaffoldsDB().nameDuplicates(self._line.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Surface Name already exists.'))
            return False

        numberOfSamples = int(self._ui.numberOfSamples.text())
        if numberOfSamples < 2:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Number of samples should be greater than or equal to two.'))
            return False

        return True

