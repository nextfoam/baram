#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QDoubleValidator, QIntValidator, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import QColorDialog
import qasync

from baramFlow.coredb.contour import Contour
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from widgets.async_message_box import AsyncMessageBox
from .colormap.colormap import colormapName, colormapImage
from .colormap_scheme_dialog import ColormapSchemeDialog
from .contour_colormap_dialog_ui import Ui_ContourColormapDialog


class ContourColormapDialog(ResizableDialog):
    def __init__(self, parent, contour: Contour):
        super().__init__(parent)
        self._ui = Ui_ContourColormapDialog()
        self._ui.setupUi(self)

        self._contour = contour

        self._dialog = None

        self._ui.fieldDisplayName.setText(contour.fieldDisplayName)
        self._ui.fieldDisplayName.setValidator(QRegularExpressionValidator(QRegularExpression('^[A-Za-z_][A-Za-z0-9_]*')))

        self._ui.numberOfLevels.setText(str(contour.numberOfLevels))
        self._ui.numberOfLevels.setValidator(QIntValidator(1, 256))

        self._ui.useNodeValues.setChecked(contour.useNodeValues)

        self._ui.relevantScaffoldsOnly.setChecked(contour.relevantScaffoldsOnly)

        self._ui.rangeMin.setText('0')
        self._ui.rangeMax.setText('0')

        self._ui.useCustomRange.setChecked(contour.useCustomRange)
        self._updateCustomRangeGroupVisibility(contour.useCustomRange)

        self._ui.customRangeMin.setText(contour.customRangeMin)
        self._ui.customRangeMin.setValidator(QDoubleValidator())

        self._ui.customRangeMax.setText(contour.customRangeMax)
        self._ui.customRangeMax.setValidator(QDoubleValidator())

        self._ui.clipToRange.setChecked(contour.clipToRange)

        self._setPresetColorScheme(contour.colorScheme)
        self._presetColorScheme = contour.colorScheme

        if contour.useCustomColorScheme:
            self._ui.useCustomColorScheme.setChecked(True)
        else:
            self._ui.usePresetColorScheme.setChecked(True)

        self._useCustomColorSchemeToggled(contour.useCustomColorScheme)

        sheet = self._getCustomColorButtonStyleSheet(contour.customMinColor)
        self._ui.customMinColor.setStyleSheet(sheet)
        self._customMinColor = contour.customMinColor

        sheet = self._getCustomColorButtonStyleSheet(contour.customMaxColor)
        self._ui.customMaxColor.setStyleSheet(sheet)
        self._customMaxColor = contour.customMaxColor

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

        self._contour.fieldDisplayName = self._ui.fieldDisplayName.text()
        self._contour.numberOfLevels = int(self._ui.numberOfLevels.text())
        self._contour.useNodeValues = True if self._ui.useNodeValues.isChecked() else False
        self._contour.relevantScaffoldsOnly = True if self._ui.relevantScaffoldsOnly.isChecked() else False
        self._contour.useCustomRange = True if self._ui.useCustomRange.isChecked() else False
        self._contour.customRangeMin = self._ui.customRangeMin.text()
        self._contour.customRangeMax = self._ui.customRangeMax.text()
        self._contour.clipToRange = True if self._ui.clipToRange.isChecked() else False
        self._contour.useCustomColorScheme = True if self._ui.useCustomColorScheme.isChecked() else False
        self._contour.colorScheme = self._presetColorScheme
        self._contour.customMinColor = self._customMinColor
        self._contour.customMaxColor = self._customMaxColor

        self._contour.markUpdated()

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
        # ToDo: jake, this is not quite natural
        rMin, rMax = self.parent().getValueRange(self._contour.field,
                                                        self._contour.vectorComponent,
                                                        self._ui.useNodeValues.isChecked(),
                                                        self._ui.relevantScaffoldsOnly.isChecked())
        self._ui.rangeMin.setText(f'{rMin:g}')
        self._ui.rangeMax.setText(f'{rMax:g}')

        self._contour.rangeMin = rMin
        self._contour.rangeMax = rMax

    def _openSchemeDialog(self):
        self._dialog = ColormapSchemeDialog(self, self._contour.colorScheme)
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

    def _setPresetColorScheme(self, scheme):
        self._ui.presetColorScheme.setText(colormapName[scheme])
        self._ui.presetColorBar.setPixmap(QPixmap(colormapImage[scheme]))
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
