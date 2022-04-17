#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from view.setup.general.general_page_ui import Ui_GeneralPage


class GeneralPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_GeneralPage()
        self._ui.setupUi(self)

    def init(self):
        pass

    def load(self):
        self._setModel("steady")

    def save(self):
        pass

    def _setModel(self, model):
        if model == "transient":
            self._ui.transient_2.setChecked(True)
        else:
            self._ui.steady.setChecked(True)

