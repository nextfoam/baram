#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .reference_values_page_ui import Ui_ReferenceValuesPage


class ReferenceValuesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ReferenceValuesPage()
        self._ui.setupUi(self)

    def load(self):
        pass

    def save(self):
        pass
