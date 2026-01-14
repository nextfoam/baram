#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import UUID
from PySide6.QtCore import QCoreApplication, QRegularExpression
from PySide6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

import qasync

from baramFlow.base.constants import FieldType
from baramFlow.base.field import CollateralField, Field
from baramFlow.base.graphic.graphic import Graphic, StreamlineType
from baramFlow.base.graphic.display_item import DisplayItem
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB
from baramFlow.base.graphic.graphics_db import GraphicsDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver_field import getAvailableFields, getSolverFieldName
from baramFlow.openfoam.openfoam_reader import OpenFOAMReader
from baramFlow.view.widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem
from baramFlow.libbaram.collateral_fields import calculateCollateralField
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.time_slider import TimeSlider

from .graphic_dialog_ui import Ui_GraphicDialog


class GraphicDialog(QDialog):
    def __init__(self, parent, graphic: Graphic, times: list[str]):
        super().__init__(parent)

        self._ui = Ui_GraphicDialog()
        self._ui.setupUi(self)

        self._STREAMLINE_TYPE_TEXTS: dict[StreamlineType, str] = None
        self._retranslateUi()

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))

        self._ui.name.setText(graphic.name)

        self._timeSlider = TimeSlider(self._ui.slider, self._ui.currentTime, self._ui.lastTime)
        self._timeSlider.updateTimeValues(times)
        self._timeSlider.setCurrentTime(graphic.time)

        self._fields: list[Field] = getAvailableFields(includeCoordinate=True)
        for f in self._fields:
            self._ui.field.addItem(f.text, f)

            if f.type == FieldType.VECTOR:
                self._ui.vectorField.addItem(f.text, f)

        # Set Configured Field into combobox
        index = self._ui.field.findData(graphic.field)
        self._ui.field.setCurrentIndex(index)

        if graphic.field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
            index = self._ui.fieldComponent.findData(graphic.fieldComponent)
            self._ui.fieldComponent.setCurrentIndex(index)
        else:
            self._ui.fieldComponent.setEnabled(False)

        index = self._ui.vectorField.findData(graphic.vectorField)
        self._ui.vectorField.setCurrentIndex(index)

        self._ui.scaleFactor.setText(graphic.vectorScaleFactor)

        self._ui.vectorFixedLength.setChecked(graphic.vectorFixedLength)

        self._graphic = graphic

        self._ui.stepSize.setText(graphic.stepSize)
        self._ui.maxSteps.setText(str(graphic.maxSteps))
        self._ui.maxLength.setText(graphic.maxLength)
        self._ui.accuracyControl.setChecked(graphic.accuracyControl)
        self._ui.tolerance.setText(graphic.tolerance)

        self._ui.stepSize.setValidator(QDoubleValidator())
        self._ui.maxSteps.setValidator(QIntValidator())
        self._ui.maxLength.setValidator(QDoubleValidator())
        self._ui.tolerance.setValidator(QDoubleValidator())

        for lineType in StreamlineType:
            self._ui.lineStyle.addItem(self.STREAMLINE_TYPE_TEXTS[lineType], lineType)
        index = self._ui.lineStyle.findData(graphic.streamlineType)
        self._ui.lineStyle.setCurrentIndex(index)

        self._ui.lineWidth.setText(graphic.lineWidth)
        self._ui.lineWidth.setValidator(QDoubleValidator())

        self._selectedScaffolds: list[UUID] = []

        self._setScaffolds(self._graphic.getScaffolds())

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.field.currentIndexChanged.connect(self._fieldChanged)
        self._ui.select.clicked.connect(self._selectClicked)
        self._ui.update.clicked.connect(self._updateClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _updateClicked(self):
        self._ui.update.setEnabled(False)
        if not await self._valid():
            self._ui.update.setEnabled(True)
            return

        fieldValueNeedUpdate = False

        time = self._timeSlider.getCurrentTime()

        field: Field = self._ui.field.currentData()
        fieldComponent = self._ui.fieldComponent.currentData()

        progressDialog = ProgressDialog(self, self.tr('Graphics Parameters'), openDelay=500)
        progressDialog.setLabelText(self.tr('Applying Graphics parameters...'))
        progressDialog.open()

        if isinstance(field, CollateralField):
            solverFieldName = getSolverFieldName(field)
            if not FileSystem.fieldExists(time, solverFieldName):
                progressDialog.setLabelText(self.tr('Calculating Collateral Field...'))

                rc = await calculateCollateralField([field], [time])

                if rc != 0:
                    progressDialog.abort(self.tr('Calculation failed'))
                    self._ui.update.setEnabled(True)
                    return

                fieldValueNeedUpdate = True

        progressDialog.setLabelText(self.tr('Applying Graphics parameters...'))

        self._graphic.name = self._ui.name.text()

        if self._graphic.time != time:
            self._graphic.time = time
            fieldValueNeedUpdate = True

        if self._graphic.field != field:
            self._graphic.field = field
            self._graphic.useCustomRange = False
            self._graphic.fieldDisplayName = self._graphic.getDefaultFieldDisplayName()
            fieldValueNeedUpdate = True

        if self._graphic.fieldComponent != fieldComponent:
            self._graphic.fieldComponent = fieldComponent
            self._graphic.fieldDisplayName = self._graphic.getDefaultFieldDisplayName()
            self._graphic.useCustomRange = False
            fieldValueNeedUpdate = True

        self._graphic.vectorField = self._ui.vectorField.currentData()
        self._graphic.vectorScaleFactor = self._ui.scaleFactor.text()
        self._graphic.vectorFixedLength = self._ui.vectorFixedLength.isChecked()

        self._graphic.stepSize = self._ui.stepSize.text()
        self._graphic.maxSteps = int(self._ui.maxSteps.text())
        self._graphic.maxLength = self._ui.maxLength.text()
        self._graphic.stepSize = self._ui.stepSize.text()
        self._graphic.accuracyControl = self._ui.accuracyControl.isChecked()
        self._graphic.tolerance = self._ui.tolerance.text()
        self._graphic.streamlineType = self._ui.lineStyle.currentData()
        self._graphic.lineWidth = self._ui.lineWidth.text()

        current = set(self._graphic.getScaffolds())
        selected = set(self._selectedScaffolds)

        removedScaffolds = current - selected
        addedScaffolds = selected - current

        for scaffoldUuid in removedScaffolds:
            await self._graphic.removeDisplayItem(scaffoldUuid)

        progressDialog.setLabelText(self.tr('Updating Graphics...'))

        async with OpenFOAMReader() as reader:
            if fieldValueNeedUpdate:
                await reader.refresh()

        await self._graphic.updatePolyMesh()

        for scaffoldUuid in addedScaffolds:
            scaffold = ScaffoldsDB().getScaffold(scaffoldUuid)
            dataSet = await scaffold.getDataSet(self._graphic.polyMesh)
            item = DisplayItem(scaffoldUuid=scaffoldUuid, dataSet=dataSet)
            await self._graphic.addDisplayItem(item)

        self._graphic.rangeMin, self._graphic.rangeMax = self._graphic.getValueRange(self._graphic.useNodeValues, self._graphic.relevantScaffoldsOnly)

        progressDialog.close()

        self._ui.update.setEnabled(True)

        super().accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        super().reject()

    async def _valid(self) -> bool:
        name = self._ui.name.text()
        if GraphicsDB().nameDuplicates(self._graphic.uuid, name):
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Graphic Name already exists.'))
            return False

        field: Field = self._ui.field.currentData()
        if field is None:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Please select valid Color-by field'))
            return False

        stepSize = float(self._ui.stepSize.text())
        if stepSize <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Step Size should be greater than zero.'))
            return False

        maxSteps = int(self._ui.maxSteps.text())
        if maxSteps <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Steps should be greater than zero.'))
            return False

        maxLength = float(self._ui.maxLength.text())
        if maxLength <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Maximum Length should be greater than zero.'))
            return False

        tolerance = float(self._ui.tolerance.text())
        if tolerance <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Tolerance should be greater than zero.'))
            return False

        lineWidth = float(self._ui.lineWidth.text())
        if lineWidth <= 0:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Line width should be greater than zero.'))
            return False

        return True

    def _fieldChanged(self, index):
        field: Field = self._ui.field.currentData()

        if field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
        else:
            self._ui.fieldComponent.setEnabled(False)

    @qasync.asyncSlot()
    async def _selectClicked(self):
        allScaffolds = [SelectorItem(s.name, s.name, str(s.uuid)) for s in ScaffoldsDB().getScaffolds().values()]
        selectedScaffolds = [str(uuid) for uuid in self._selectedScaffolds]
        self._dialog = MultiSelectorDialog(self, self.tr("Select Scaffolds"), allScaffolds, selectedScaffolds)
        self._dialog.accepted.connect(self._scaffoldsChanged)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _scaffoldsChanged(self):
        scaffoldUuidList = [UUID(uuidStr) for uuidStr in self._dialog.selectedItems()]
        self._setScaffolds(scaffoldUuidList)

    def _setScaffolds(self, scaffoldUuidList: list[UUID]):
        self._selectedScaffolds = scaffoldUuidList
        self._ui.scaffolds.clear()
        for uuid in scaffoldUuidList:
            s = ScaffoldsDB().getScaffold(uuid)
            self._ui.scaffolds.addItem(s.name)

    def _retranslateUi(self):
        self.STREAMLINE_TYPE_TEXTS = {
            StreamlineType.LINE: QCoreApplication.translate('GraphicDialog', 'Line'),
            StreamlineType.RIBBON: QCoreApplication.translate('GraphicDialog', 'Ribbon'),
        }

