#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.dialog.pane_page import PanePage
from view.dialog.setup.general.general_page_ui import Ui_GeneralPage


class GeneralPage(PanePage):
    def __init__(self):
        super().__init__(Ui_GeneralPage())

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

