#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Pane:
    def __init__(self):
        self._index = -1
        self._ui = None

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, index):
        self._index = index

    @property
    def ui(self):
        return self._ui

    @ui.setter
    def ui(self, ui):
        self._ui = ui

    # virtual
    def create_page(self):
        pass

    def init(self):
        self._ui.init()

    # virtual
    def load(self):
        pass

    # virtual
    def save(self):
        pass
