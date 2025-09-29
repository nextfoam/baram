#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

from baramFlow.base.constants import FieldType, VectorComponent
from baramFlow.base.field import CollateralField, Field
from baramFlow.openfoam.solver_field import getAvailableFields
from baramFlow.base.scaffold.iso_surface import IsoSurface
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB

from baramFlow.openfoam.file_system import FileSystem
from baramFlow.libbaram.util import getScalarRange, getVectorRange
from baramFlow.openfoam.solver_field import getSolverFieldName
from baramFlow.openfoam.openfoam_reader import OpenFOAMReader
from baramFlow.libbaram.collateral_fields import calculateCollateralField
from libbaram.openfoam.polymesh import collectInternalMesh
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.time_slider import TimeSlider

from .iso_surface_dialog_ui import Ui_IsoSurfaceDialog


class IsoSurfaceDialog(QDialog):
    def __init__(self, parent, surface: IsoSurface, times: list[str], isNew=False):
        super().__init__(parent)

        self._ui = Ui_IsoSurfaceDialog()
        self._ui.setupUi(self)

        self._surface = surface

        self._fields = getAvailableFields(includeCoordinate=True)

        for f in self._fields:
            self._ui.field.addItem(f.text, f)

        # Set Configured Field into combobox
        index = self._ui.field.findData(surface.field)
        self._ui.field.setCurrentIndex(index)

        if surface.field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
            index = self._ui.fieldComponent.findData(surface.fieldComponent)
            self._ui.fieldComponent.setCurrentIndex(index)
        else:
            self._ui.fieldComponent.setEnabled(False)

        if isNew:
            self._ui.ok.setText('Create')

        self._timeSlider = TimeSlider(self._ui.slider, self._ui.currentTime, self._ui.lastTime)
        self._timeSlider.updateTimeValues(times)
        self._timeSlider.setCurrentTime(times[-1])

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
        self._ui.field.currentIndexChanged.connect(self._fieldChanged)
        self._ui.computeRange.clicked.connect(self._computeRangeClicked)
        self._ui.surfacesPerValue.valueChanged.connect(self._surfacesPerValueChanged)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _computeRangeClicked(self):
        time = self._timeSlider.getCurrentTime()
        field: Field = self._ui.field.currentData()
        fieldComponent: VectorComponent = self._ui.fieldComponent.currentData()

        progressDialog = ProgressDialog(self, self.tr('Range Calculation'))
        progressDialog.setLabelText(self.tr('Computing range...'))
        progressDialog.open()

        if isinstance(field, CollateralField):
            solverFieldName = getSolverFieldName(field)
            if not FileSystem.fieldExists(time, solverFieldName):
                progressDialog.setLabelText(self.tr('Calculating Collateral Field...'))

                rc = await calculateCollateralField([field], [time])

                if rc != 0:
                    progressDialog.finish(self.tr('Calculation failed'))
                    return

        progressDialog.setLabelText(self.tr('Computing range...'))

        async with OpenFOAMReader() as reader:
            await reader.refresh()

            reader.setTimeValue(float(time))
            await reader.update()
            mBlock = reader.getOutput()

            mesh = await collectInternalMesh(mBlock)
            if field.type == FieldType.VECTOR:
                rangeMin, rangeMax = getVectorRange(mesh, field, fieldComponent, useNodeValues=True)
            else:
                rangeMin, rangeMax = getScalarRange(mesh, field, useNodeValues=True)

        self._ui.rangeMin.setText(f'{rangeMin:.4g}')
        self._ui.rangeMax.setText(f'{rangeMax:.4g}')

        progressDialog.close()

    @qasync.asyncSlot()
    async def _surfacesPerValueChanged(self, value):
        self._ui.spacing.setEnabled(value > 1)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._surface.name = self._ui.name.text()
        self._surface.field = self._ui.field.currentData()
        self._surface.fieldComponent = self._ui.fieldComponent.currentData()
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

    def _fieldChanged(self, index):
        field: Field = self._ui.field.currentData()

        if field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
        else:
            self._ui.fieldComponent.setEnabled(False)
