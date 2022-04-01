#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .general_page import GeneralPage
from .pane import Pane


class GeneralPane(Pane):
    def __init__(self):
        super().__init__()

    def create_page(self):
        self._ui = GeneralPage()
        return self._ui

    def load(self):
        self._ui.setModel("steady")

    def save(self):
        pass



