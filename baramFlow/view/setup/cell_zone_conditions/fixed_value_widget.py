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

        self._db = coredb.CoreDB()
        self._title = title
        self._xpath = xpath

        self._ui.groupBox.setTitle(title)
        self._ui.label.setText(label)

    def load(self):
        self._ui.groupBox.setChecked(self._db.getAttribute(self._xpath, 'disabled') == 'false')
        self._ui.value.setText(self._db.getValue(self._xpath))

    def appendToWriter(self, writer):
        if self._ui.groupBox.isChecked():
            writer.setAttribute(self._xpath, 'disabled', 'false')
            writer.append(self._xpath, self._ui.value.text(), self._title)
        else:
            writer.setAttribute(self._xpath, 'disabled', 'true')

        return True
