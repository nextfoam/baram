#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.coredb.post_field import BasicField, getAvailableFields
from baramFlow.view.results.results_model.post_field import FIELD_TEXTS
from libbaram.mesh import Bounds
from widgets.async_message_box import AsyncMessageBox
from widgets.rendering.point_widget import PointWidget
from widgets.selector_dialog import SelectorDialog

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.mesh.vtk_loader import isPointInDataSet
from .iso_surface_dialog_ui import Ui_IsoSurfaceDialog


class IsoSurfaceDialog(QDialog):
    TEXT_FOR_NONE_BOUNDARY = 'None'

    def __init__(self, parent, surface: IsoSurface, isNew=False):
        super().__init__(parent)

        self._ui = Ui_IsoSurfaceDialog()
        self._ui.setupUi(self)

        self._surface = surface

        self._fields: list[Field] = getAvailableFields()
        for f in self._fields:
            if f in FIELD_TEXTS:
                self._ui.field.addItem(FIELD_TEXTS[f], f)
            else:
                self._ui.field.addItem(f.name, f)

        index = self._ui.field.findData(surface.field)
        self._ui.field.setCurrentIndex(index)

        if isNew:
            self._ui.ok.setText('Create')

        # u0 = BasicField('jake0')
        # u1 = BasicField('jake1')
        # u2 = BasicField('jake2')
        # u3 = BasicField('jake3')
        # u4 = BasicField('jake4')

        # self._ui.field.addItem(u0.name, u0)
        # self._ui.field.addItem(u1.name, u1)
        # self._ui.field.addItem(u2.name, u2)
        # self._ui.field.addItem(u3.name, u3)
        # self._ui.field.addItem(u4.name, u4)

        # u = BasicField('jake2')
        # index = self._ui.field.findData(u)
        # print(index)
        # self._ui.field.setCurrentIndex(index)

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))
        self._ui.spacing.setValidator(QDoubleValidator())

        self._ui.name.setText(surface.name)

        index = self._ui.field.findData(surface.field)
        self._ui.field.setCurrentIndex(index)

        self._ui.isoValues.setText(surface.isoValues)
        self._ui.surfacesPerValue.setValue(surface.surfacePerValue)
        self._ui.spacing.setText(surface.spacing)

        self._ui.spacing.setEnabled(self._ui.surfacesPerValue.value() > 1)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.computeRange.clicked.connect(self._computeRangeClicked)
        self._ui.surfacesPerValue.valueChanged.connect(self._surfacesPerValueChanged)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _computeRangeClicked(self):
        pass

    @qasync.asyncSlot()
    async def _surfacesPerValueChanged(self, value):
        self._ui.spacing.setEnabled(value > 1)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._surface.name = self._ui.name.text()
        self._surface.field = self._ui.field.currentData()
        self._surface.isoValues = self._ui.isoValues.text().strip()
        self._surface.surfacePerValue = self._ui.surfacesPerValue.value()
        self._surface.spacing = self._ui.spacing.text().strip()

        self.accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        self.reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if ScaffoldsDB().nameDuplicates(self._surface.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Surface Name already exists.'))
            return False

        strings = self._ui.isoValues.text().split()

        if not strings:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('No value for Iso-Values'))
            return False

        for s in self._ui.isoValues.text().split():
            try:
                float(s)
            except ValueError:
                await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                 self.tr('Invalid value for Iso-Values'))
                return False

        try:
            if float(self._ui.spacing.text()) <= 0:
                raise ValueError
        except ValueError:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Spacing value should be greater than zero'))
            return False

        return True
