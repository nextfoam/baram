#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .pane_page import PanePage
from .general_page_ui import Ui_GeneralPage


class GeneralPage(PanePage):
    def __init__(self):
        super().__init__(Ui_GeneralPage())
        self._ui.setupUi(self)

    def init(self):
        pass

    def setModel(self, model):
        if model == "transient":
            self._ui.transient_2.setChecked(True)
        else:
            self._ui.steady.setChecked(True)

