#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import SpecificationMethod
from .constant_source_widget_ui import Ui_ConstantSourceWidget


class ConstantSourceWidget(QWidget):
    def __init__(self, title, label, units, xpath):
        """Constructs a new widget for setting the fixed value of the cell zone conditions.

        Args:
            title: title of the groupBox
            label: label of the value
            xpath: xpath for the coredb
        """
        super().__init__()
        self._ui = Ui_ConstantSourceWidget()
        self._ui.setupUi(self)

        self._title = title
        self._xpath = xpath
        self._label = label
        self._units = units

        self._ui.groupBox.setTitle(title)
        self._ui.label.setText(label)

        self._ui.specificationMethod.addEnumItems({
            SpecificationMethod.VALUE_PER_UNIT_VOLUME: self.tr("Value per Unit Volume"),
            SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: self.tr("Value for Entire Cell Zone"),
        })

        self._connectSignalsSlots()

    def load(self):
        db = coredb.CoreDB()
        self._ui.groupBox.setChecked(db.getAttribute(self._xpath, 'disabled') == 'false')
        self._ui.specificationMethod.setCurrentData(SpecificationMethod(db.getValue(self._xpath + '/unit')))
        self._ui.value.setText(db.getValue(self._xpath + '/constant'))

    def updateDB(self, newDB):
        if self._ui.groupBox.isChecked():
            newDB.setAttribute(self._xpath, 'disabled', 'false')
            newDB.setValue(self._xpath + '/unit', self._ui.specificationMethod.currentValue(), None)
            newDB.setValue(self._xpath + '/constant', self._ui.value.text(), self._title)
        else:
            newDB.setAttribute(self._xpath, 'disabled', 'true')

        return True

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)

    def _specificationMethodChanged(self, method):
        self._ui.label.setText(f'{self._label} ({self._units.get(method, "")})')
