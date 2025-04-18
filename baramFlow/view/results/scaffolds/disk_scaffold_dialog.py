#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.base.scaffold.disk_scaffold import DiskScaffold
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB

from widgets.async_message_box import AsyncMessageBox

from .disk_scaffold_dialog_ui import Ui_DiskScaffoldDialog


class DiskScaffoldDialog(QDialog):
    def __init__(self, parent, disk: DiskScaffold, isNew=False):
        super().__init__(parent)

        self._ui = Ui_DiskScaffoldDialog()
        self._ui.setupUi(self)

        self._disk = disk

        if isNew:
            self._ui.ok.setText('Create')

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))

        self._ui.centerX.setValidator(QDoubleValidator())
        self._ui.centerY.setValidator(QDoubleValidator())
        self._ui.centerZ.setValidator(QDoubleValidator())

        self._ui.normalX.setValidator(QDoubleValidator())
        self._ui.normalY.setValidator(QDoubleValidator())
        self._ui.normalZ.setValidator(QDoubleValidator())

        self._ui.outerRadius.setValidator(QDoubleValidator())
        self._ui.innerRadius.setValidator(QDoubleValidator())

        self._ui.radialSamples.setValidator(QIntValidator())
        self._ui.circumferentialSamples.setValidator(QIntValidator())

        self._ui.name.setText(disk.name)

        self._ui.centerX.setText(disk.centerX)
        self._ui.centerY.setText(disk.centerY)
        self._ui.centerZ.setText(disk.centerZ)

        self._ui.normalX.setText(disk.normalX)
        self._ui.normalY.setText(disk.normalY)
        self._ui.normalZ.setText(disk.normalZ)

        self._ui.outerRadius.setText(disk.outerRadius)
        self._ui.innerRadius.setText(disk.innerRadius)

        self._ui.radialSamples.setText(str(disk.radialSamples))
        self._ui.circumferentialSamples.setText(str(disk.circumferentialSamples))

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._disk.name = self._ui.name.text()

        self._disk.centerX = self._ui.centerX.text()
        self._disk.centerY = self._ui.centerY.text()
        self._disk.centerZ = self._ui.centerZ.text()

        self._disk.normalX = self._ui.normalX.text()
        self._disk.normalY = self._ui.normalY.text()
        self._disk.normalZ = self._ui.normalZ.text()

        self._disk.outerRadius = self._ui.outerRadius.text()
        self._disk.innerRadius = self._ui.innerRadius.text()

        self._disk.radialSamples = int(self._ui.radialSamples.text())
        self._disk.circumferentialSamples = int(self._ui.circumferentialSamples.text())

        self.accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        self.reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if ScaffoldsDB().nameDuplicates(self._disk.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Surface Name already exists.'))
            return False

        outerRadius = float(self._ui.outerRadius.text())
        if outerRadius <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Outer Radius should be greater than zero.'))
            return False

        innerRadius = float(self._ui.innerRadius.text())
        if innerRadius < 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Inner Radius should not be negative value.'))
            return False

        radialSamples = int(self._ui.radialSamples.text())
        if radialSamples <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Radial number of samples should be greater than zero.'))
            return False

        circumferentialSamples = int(self._ui.circumferentialSamples.text())
        if circumferentialSamples <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Circumferential number of samples should be greater than zero.'))
            return False

        return True

