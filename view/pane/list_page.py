#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .pane_page import PanePage


class ListPage(PanePage):
    def __init__(self, widget):
        super().__init__(widget)

    def init(self):
        self._ui.editList.clear()

    def add(self, text):
        self._ui.editList.addItem(text)
