#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QColorDialog, QHBoxLayout
import qasync

from baramFlow.base.graphic.color_scheme import ColorbarWidget, ColormapScheme
from baramFlow.base.graphic.graphic import Graphic
from baramFlow.base.field import VECTOR_COMPONENT_TEXTS, FieldType
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from baramFlow.base.graphic.color_scheme import colormapName
from .colormap_scheme_dialog import ColormapSchemeDialog
from .colormap_dialog_ui import Ui_ColormapDialog


class ColormapDialog(ResizableDialog):
    def __init__(self, parent, graphic: Graphic):
        super().__init__(parent)
        self._ui = Ui_ColormapDialog()
        self._ui.setupUi(self)

        self._graphic = graphic

        self._dialog = None
        self._colorbarWidget = None

        self._colorbarLayout = QHBoxLayout(self._ui.presetColorBar)
        self._colorbarLayout.setContentsMargins(0, 0, 0, 0)

        self._ui.fieldDisplayName.setText(graphic.fieldDisplayName)
        self._ui.fieldDisplayName.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_]*')))

        self._ui.numberOfLevels.setText(str(graphic.numberOfLevels))
        self._ui.numberOfLevels.setValidator(QIntValidator(1, 256))

        self._ui.useNodeValues.setChecked(graphic.useNodeValues)

        self._ui.relevantScaffoldsOnly.setChecked(graphic.relevantScaffoldsOnly)

        fieldName = graphic.field.text

        if graphic.field.type == FieldType.VECTOR:
            fieldName += '  ( ' + VECTOR_COMPONENT_TEXTS[graphic.fieldComponent] + ' )'

        self._ui.colorBy.setText(fieldName)

        self._ui.rangeMin.setText(f'{graphic.rangeMin:g}')
        self._ui.rangeMax.setText(f'{graphic.rangeMax:g}')

        self._ui.useCustomRange.setChecked(graphic.useCustomRange)
        self._updateCustomRangeGroupVisibility(graphic.useCustomRange)

        self._ui.customRangeMin.setText(graphic.customRangeMin)
        self._ui.customRangeMin.setValidator(QDoubleValidator())

        self._ui.customRangeMax.setText(graphic.customRangeMax)
        self._ui.customRangeMax.setValidator(QDoubleValidator())

        self._ui.clipToRange.setChecked(graphic.clipToRange)

        self._setPresetColorScheme(graphic.colorScheme)
        self._presetColorScheme = graphic.colorScheme

        if graphic.useCustomColorScheme:
            self._ui.useCustomColorScheme.setChecked(True)
        else:
            self._ui.usePresetColorScheme.setChecked(True)

        self._useCustomColorSchemeToggled(graphic.useCustomColorScheme)

        sheet = self._getCustomColorButtonStyleSheet(graphic.customMinColor)
        self._ui.customMinColor.setStyleSheet(sheet)
        self._customMinColor = graphic.customMinColor

        sheet = self._getCustomColorButtonStyleSheet(graphic.customMaxColor)
        self._ui.customMaxColor.setStyleSheet(sheet)
        self._customMaxColor = graphic.customMaxColor

        self._updateCustomColorBar()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.computeRange.clicked.connect(self._computeRange)
        self._ui.useCustomRange.stateChanged.connect(self._updateCustomRangeGroupVisibility)
        self._ui.useCustomColorScheme.toggled.connect(self._useCustomColorSchemeToggled)
        self._ui.customMinColor.clicked.connect(self._customMinColorClicked)
        self._ui.customMaxColor.clicked.connect(self._customMaxColorClicked)
        self._ui.select.clicked.connect(self._openSchemeDialog)
        self._ui.ok.clicked.connect(self._okClicked)
        self._ui.cancel.clicked.connect(self._cancelClicked)

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not await self._valid():
            return

        self._graphic.fieldDisplayName = self._ui.fieldDisplayName.text()
        self._graphic.numberOfLevels = int(self._ui.numberOfLevels.text())
        self._graphic.useNodeValues = True if self._ui.useNodeValues.isChecked() else False
        self._graphic.relevantScaffoldsOnly = True if self._ui.relevantScaffoldsOnly.isChecked() else False
        self._graphic.useCustomRange = True if self._ui.useCustomRange.isChecked() else False
        self._graphic.customRangeMin = self._ui.customRangeMin.text()
        self._graphic.customRangeMax = self._ui.customRangeMax.text()
        self._graphic.clipToRange = True if self._ui.clipToRange.isChecked() else False
        self._graphic.useCustomColorScheme = True if self._ui.useCustomColorScheme.isChecked() else False
        self._graphic.colorScheme = self._presetColorScheme
        self._graphic.customMinColor = self._customMinColor
        self._graphic.customMaxColor = self._customMaxColor

        progressDialog = ProgressDialog(self, self.tr('Graphics Parameters'), openDelay=500)
        progressDialog.setLabelText(self.tr('Applying Graphics parameters...'))
        progressDialog.open()

        await self._graphic.notifyReportUpdated()

        progressDialog.close()

        super().accept()

    @qasync.asyncSlot()
    async def _cancelClicked(self):
        super().reject()

    async def _valid(self) -> bool:
        if self._ui.useCustomRange.isChecked():
            rangeMin = float(self._ui.customRangeMin.text())
            rangeMax = float(self._ui.customRangeMax.text())
            if rangeMin >= rangeMax:
                await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                    self.tr('Custom Range Max should be greater than Custom Range Min'))
                return False

        numberOfLevels = int(self._ui.numberOfLevels.text())
        if numberOfLevels < 1:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Number of levels should be greater than 0'))
            return False

        if numberOfLevels > 256:
            await AsyncMessageBox().critical(self, self.tr('Input Error'),
                                                self.tr('Number of levels should be less than 257'))
            return False

        return True

    def _computeRange(self):
        rMin, rMax = self._graphic.getValueRange(self._ui.useNodeValues.isChecked(),
                                                 self._ui.relevantScaffoldsOnly.isChecked())
        self._ui.rangeMin.setText(f'{rMin:g}')
        self._ui.rangeMax.setText(f'{rMax:g}')

        self._graphic.rangeMin = rMin
        self._graphic.rangeMax = rMax

    def _openSchemeDialog(self):
        self._dialog = ColormapSchemeDialog(self, self._presetColorScheme)
        self._dialog.schemeSelected.connect(self._setPresetColorScheme)
        self._dialog.open()

    def _updateCustomRangeGroupVisibility(self, checked):
        self._ui.customRangeGroup.setVisible(checked)

    def _useCustomColorSchemeToggled(self, checked: bool):
        if checked:
            self._ui.customSchemeGroup.show()
            self._ui.presetSchemeGroup.hide()
        else:
            self._ui.customSchemeGroup.hide()
            self._ui.presetSchemeGroup.show()

    def _setPresetColorScheme(self, scheme: ColormapScheme):
        self._ui.presetColorScheme.setText(colormapName[scheme])

        if self._colorbarWidget is not None:
            self._colorbarLayout.removeWidget(self._colorbarWidget)

        self._colorbarWidget = ColorbarWidget(scheme, 240, 20)
        self._colorbarLayout.addWidget(self._colorbarWidget)

        self._presetColorScheme = scheme

    def _customMinColorClicked(self):
        self._dialog = QColorDialog(self._customMinColor, self)
        self._dialog.colorSelected.connect(self._customMinColorSelected)
        self._dialog.open()

    def _customMaxColorClicked(self):
        self._dialog = QColorDialog(self._customMaxColor, self)
        self._dialog.colorSelected.connect(self._customMaxColorSelected)
        self._dialog.open()

    def _customMinColorSelected(self, color: QColor):
        sheet = self._getCustomColorButtonStyleSheet(color)
        self._ui.customMinColor.setStyleSheet(sheet)
        self._customMinColor = color
        self._updateCustomColorBar()

    def _customMaxColorSelected(self, color: QColor):
        sheet = self._getCustomColorButtonStyleSheet(color)
        self._ui.customMaxColor.setStyleSheet(sheet)
        self._customMaxColor = color
        self._updateCustomColorBar()

    def _getCustomColorButtonStyleSheet(self, color: QColor):
        r, g, b, a = color.getRgb()
        return f'background: rgb({r}, {g}, {b}); border-style: solid; border-color:black; border-width: 1'

    def _updateCustomColorBar(self):
        self._ui.customColorBar.setStyleSheet(
            f'background-color: qlineargradient(x1: 0, y1: 0,x2: 1, y2: 0, stop: 0 {self._customMinColor.name()}, stop: 1 {self._customMaxColor.name()});'
            'border-style: solid; border-color:black; border-width: 1;')
