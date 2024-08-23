#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from .fixed_value_widget_ui import Ui_FixedValueWidget


class FixedValueWidget(QWidget):
    def __init__(self, title, label, xpath):
        """Constructs a new widget for setting the fixed value of the cell zone conditions.

        Args:
            title: title of the groupBox
            label: label of the value
            xpath: xpath for the coredb
        """
        super().__init__()
        self._ui = Ui_FixedValueWidget()
        self._ui.setupUi(self)

        self._title = title
        self._xpath = xpath

        self._ui.groupBox.setTitle(title)
        self._ui.label.setText(label)

    def setChecked(self, checked):
        self._ui.groupBox.setChecked(checked)

    def load(self):
        db = coredb.CoreDB()
        if db.exists(self._xpath):
            self._ui.groupBox.setChecked(db.getAttribute(self._xpath, 'disabled') == 'false')
            self._ui.value.setText(db.getValue(self._xpath))
        else:
            self._ui.groupBox.setChecked(False)

    def updateDB(self, newDB):
        if self._ui.groupBox.isChecked():
            newDB.setAttribute(self._xpath, 'disabled', 'false')
            newDB.setValue(self._xpath, self._ui.value.text(), self._title)
        else:
            newDB.setAttribute(self._xpath, 'disabled', 'true')

        return True
