#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .general_page import GeneralPage
from .pane import Pane


class GeneralPane(Pane):
    def __init__(self):
        super().__init__()

    def create_page(self):
        return GeneralPage()

    def load(self, ui):
        ui.setModel("steady")

    def save(self):
        pass



