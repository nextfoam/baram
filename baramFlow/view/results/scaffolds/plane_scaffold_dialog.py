#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.base.scaffold.plane_scaffold import PlaneScaffold
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB

from widgets.async_message_box import AsyncMessageBox

from .plane_scaffold_dialog_ui import Ui_PlaneScaffoldDialog


class PlaneScaffoldDialog(QDialog):
    def __init__(self, parent, plane: PlaneScaffold, isNew=False):
        super().__init__(parent)

        self._ui = Ui_PlaneScaffoldDialog()
        self._ui.setupUi(self)

        self._plane = plane

        if isNew:
            self._ui.ok.setText('Create')

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))

        self._ui.originX.setValidator(QDoubleValidator())
        self._ui.originY.setValidator(QDoubleValidator())
        self._ui.originZ.setValidator(QDoubleValidator())

        self._ui.normalX.setValidator(QDoubleValidator())
        self._ui.normalY.setValidator(QDoubleValidator())
        self._ui.normalZ.setValidator(QDoubleValidator())

        self._ui.name.setText(plane.name)

        self._ui.originX.setText(plane.originX)
        self._ui.originY.setText(plane.originY)
        self._ui.originZ.setText(plane.originZ)

        self._ui.normalX.setText(plane.normalX)
        self._ui.normalY.setText(plane.normalY)
        self._ui.normalZ.setText(plane.normalZ)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._plane.name = self._ui.name.text()

        self._plane.originX = self._ui.originX.text()
        self._plane.originY = self._ui.originY.text()
        self._plane.originZ = self._ui.originZ.text()

        self._plane.normalX = self._ui.normalX.text()
        self._plane.normalY = self._ui.normalY.text()
        self._plane.normalZ = self._ui.normalZ.text()

        self.accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        self.reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if ScaffoldsDB().nameDuplicates(self._plane.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Surface Name already exists.'))
            return False

        return True

