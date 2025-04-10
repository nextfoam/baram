#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import UUID
from PySide6.QtCore import QCoreApplication, QRegularExpression
from PySide6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog

import qasync

from baramFlow.coredb.contour import Contour, StreamlineType
from baramFlow.coredb.post_field import CollateralField, Field, FieldType, getAvailableFields
from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.visual_reports_db import VisualReportsDB
from baramFlow.coredb.post_field import FIELD_TEXTS
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver_field import getSolverFieldName
from baramFlow.view.results.visual_reports.openfoam_reader import OpenFOAMReader
from baramFlow.view.widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem
from libbaram.openfoam.collateral_fields import calculateCollateralField
from libbaram.openfoam.polymesh import collectInternalMesh
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.time_slider import TimeSlider

from .contour_dialog_ui import Ui_ContourDialog


class ContourDialog(QDialog):
    def __init__(self, parent, contour: Contour, times: list[str]):
        super().__init__(parent)

        self._ui = Ui_ContourDialog()
        self._ui.setupUi(self)

        self._STREAMLINE_TYPE_TEXTS: dict[StreamlineType, str] = None
        self._retranslateUi()

        self._ui.name.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_-]*')))

        self._ui.name.setText(contour.name)

        self._timeSlider = TimeSlider(self._ui.slider, self._ui.currentTime, self._ui.lastTime)
        self._timeSlider.updateTimeValues(times)
        self._timeSlider.setCurrentTime(contour.time)

        self._fields: list[Field] = getAvailableFields()
        for f in self._fields:
            if f in FIELD_TEXTS:
                text = FIELD_TEXTS[f]
            else:
                text = f.codeName

            self._ui.field.addItem(text, f)

            if f.type == FieldType.VECTOR:
                self._ui.vectorField.addItem(text, f)

        # Set Configured Field into combobox
        index = self._ui.field.findData(contour.field)
        self._ui.field.setCurrentIndex(index)

        if contour.field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
            index = self._ui.fieldComponent.findData(contour.fieldComponent)
            self._ui.fieldComponent.setCurrentIndex(index)
        else:
            self._ui.fieldComponent.setEnabled(False)

        self._ui.includeVectors.setChecked(contour.includeVectors)

        index = self._ui.vectorField.findData(contour.vectorField)
        self._ui.vectorField.setCurrentIndex(index)

        self._ui.scaleFactor.setText(contour.vectorScaleFactor)

        self._contour = contour

        self._ui.stepSize.setText(contour.stepSize)
        self._ui.maxSteps.setText(str(contour.maxSteps))
        self._ui.maxLength.setText(contour.maxLength)
        self._ui.accuracyControl.setChecked(contour.accuracyControl)
        self._ui.tolerance.setText(contour.tolerance)

        self._ui.stepSize.setValidator(QDoubleValidator())
        self._ui.maxSteps.setValidator(QIntValidator())
        self._ui.maxLength.setValidator(QDoubleValidator())
        self._ui.tolerance.setValidator(QDoubleValidator())

        for lineType in StreamlineType:
            self._ui.lineStyle.addItem(self.STREAMLINE_TYPE_TEXTS[lineType], lineType)
        index = self._ui.lineStyle.findData(contour.streamlineType)
        self._ui.lineStyle.setCurrentIndex(index)

        self._ui.lineWidth.setText(contour.lineWidth)
        self._ui.lineWidth.setValidator(QDoubleValidator())

        self._selectedScaffolds: list[UUID] = []

        self._setScaffolds(list(self._contour.reportingScaffolds.keys()))

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.field.currentIndexChanged.connect(self._fieldChanged)
        self._ui.select.clicked.connect(self._selectClicked)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
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
                    progressDialog.finish(self.tr('Calculation failed'))
                    return

                fieldValueNeedUpdate = True

        progressDialog.setLabelText(self.tr('Applying Graphics parameters...'))

        self._contour.name = self._ui.name.text()

        if self._contour.time != time:
            self._contour.time = time
            fieldValueNeedUpdate = True

        if self._contour.field != field:
            self._contour.field = field
            fieldValueNeedUpdate = True

        if self._contour.fieldComponent != fieldComponent:
            self._contour.fieldComponent = fieldComponent
            fieldValueNeedUpdate = True

        self._contour.includeVectors = self._ui.includeVectors.isChecked()
        self._contour.vectorField = self._ui.vectorField.currentData()
        self._contour.vectorScaleFactor = self._ui.scaleFactor.text()

        self._contour.stepSize = self._ui.stepSize.text()
        self._contour.maxSteps = int(self._ui.maxSteps.text())
        self._contour.maxLength = self._ui.maxLength.text()
        self._contour.stepSize = self._ui.stepSize.text()
        self._contour.accuracyControl = self._ui.accuracyControl.isChecked()
        self._contour.tolerance = self._ui.tolerance.text()
        self._contour.streamlineType = self._ui.lineStyle.currentData()
        self._contour.lineWidth = self._ui.lineWidth.text()

        current = set(self._contour.reportingScaffolds.keys())
        selected = set(self._selectedScaffolds)

        removedScaffolds = current - selected
        addedScaffolds = selected - current

        for uuid in removedScaffolds:
            await self._contour.notifyScaffoldRemoving(uuid)
            del self._contour.reportingScaffolds[uuid]
            await self._contour.notifyReportingScaffoldRemoved(uuid)


        progressDialog.setLabelText(self.tr('Updating Graphics...'))

        async with OpenFOAMReader() as reader:
            if fieldValueNeedUpdate:
                await reader.refresh()

            reader.setTimeValue(float(self._contour.time))
            await reader.update()
            mBlock = reader.getOutput()

            self._contour.polyMesh = mBlock
            self._contour.internalMesh = collectInternalMesh(mBlock)

            if fieldValueNeedUpdate:  # field values in internalMesh have changed
                for uuid, rs in self._contour.reportingScaffolds.items():
                    scaffold = ScaffoldsDB().getScaffold(uuid)
                    rs.dataSet = await scaffold.getDataSet(mBlock)

            for uuid in addedScaffolds:
                scaffold = ScaffoldsDB().getScaffold(uuid)
                dataSet = await scaffold.getDataSet(mBlock)
                rs = ReportingScaffold(scaffoldUuid=uuid, dataSet=dataSet)
                self._contour.reportingScaffolds[uuid] = rs
                await self._contour.notifyReportingScaffoldAdded(uuid)

        progressDialog.close()

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
            StreamlineType.LINE: QCoreApplication.translate('ContourDialog', 'Line'),
            StreamlineType.RIBBON: QCoreApplication.translate('ContourDialog', 'Ribbon'),
        }

