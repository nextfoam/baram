#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from coredb.cell_zone_db import SpecificationMethod
from .constant_source_widget_ui import Ui_ConstantSourceWidget


class ConstantSourceWidget(QWidget):
    def __init__(self, title, label, xpath):
        """Constructs a new widget for setting the fixed value of the cell zone conditions.

        Args:
            title: title of the groupBox
            label: label of the value
            xpath: xpath for the coredb
        """
        super().__init__()
        self._ui = Ui_ConstantSourceWidget()
        self._ui.setupUi(self)

        self._specificationMethods = {
            SpecificationMethod.VALUE_PER_UNIT_VOLUME.value: self.tr("Value per Unit Volume"),
            SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE.value: self.tr("Value for Entire Cell Zone"),
        }

        self._db = coredb.CoreDB()
        self._title = title
        self._xpath = xpath

        self._ui.groupBox.setTitle(title)
        self._ui.label.setText(label)

        self._setupSpecificationCombo()

    def load(self):
        self._ui.groupBox.setChecked(self._db.getAttribute(self._xpath, 'disabled') == 'false')
        self._ui.specificationMethod.setCurrentText(
            self._specificationMethods[self._db.getValue(self._xpath + '/unit')])
        self._ui.value.setText(self._db.getValue(self._xpath + '/constant'))

    def appendToWriter(self, writer):
        if self._ui.groupBox.isChecked():
            writer.setAttribute(self._xpath, 'disabled', 'false')
            writer.append(self._xpath + '/unit', self._ui.specificationMethod.currentData(), None)
            writer.append(self._xpath + '/constant', self._ui.value.text(), self._title)
        else:
            writer.setAttribute(self._xpath, 'disabled', 'true')

        return True

    def _setupSpecificationCombo(self):
        for value, text in self._specificationMethods.items():
            self._ui.specificationMethod.addItem(text, value)
