#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.base.scaffold.sphere_scaffold import SphereScaffold
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB

from widgets.async_message_box import AsyncMessageBox

from .sphere_scaffold_dialog_ui import Ui_SphereScaffoldDialog


class SphereScaffoldDialog(QDialog):
    def __init__(self, parent, sphere: SphereScaffold, isNew=False):
        super().__init__(parent)

        self._ui = Ui_SphereScaffoldDialog()
        self._ui.setupUi(self)

        self._sphere = sphere

        if isNew:
            self._ui.ok.setText('Create')

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))

        self._ui.centerX.setValidator(QDoubleValidator())
        self._ui.centerY.setValidator(QDoubleValidator())
        self._ui.centerZ.setValidator(QDoubleValidator())

        self._ui.radius.setValidator(QDoubleValidator())

        self._ui.longitudeSamples.setValidator(QIntValidator())
        self._ui.latitudeSamples.setValidator(QIntValidator())

        self._ui.name.setText(sphere.name)

        self._ui.centerX.setText(sphere.centerX)
        self._ui.centerY.setText(sphere.centerY)
        self._ui.centerZ.setText(sphere.centerZ)

        self._ui.radius.setText(sphere.radius)

        self._ui.longitudeSamples.setText(str(sphere.longitudeSamples))
        self._ui.latitudeSamples.setText(str(sphere.latitudeSamples))

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._sphere.name = self._ui.name.text()

        self._sphere.centerX = self._ui.centerX.text()
        self._sphere.centerY = self._ui.centerY.text()
        self._sphere.centerZ = self._ui.centerZ.text()

        self._sphere.radius = self._ui.radius.text()

        self._sphere.longitudeSamples = int(self._ui.longitudeSamples.text())
        self._sphere.latitudeSamples = int(self._ui.latitudeSamples.text())

        self.accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        self.reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if ScaffoldsDB().nameDuplicates(self._sphere.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Surface Name already exists.'))
            return False

        radius = float(self._ui.radius.text())
        if radius <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Radius should be greater than zero.'))
            return False

        longitudeSamples = int(self._ui.longitudeSamples.text())
        latitudeSamples = int(self._ui.latitudeSamples.text())
        if longitudeSamples < 4 or latitudeSamples < 4:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Number of samples should be greater than or equal to four.'))
            return False

        return True
