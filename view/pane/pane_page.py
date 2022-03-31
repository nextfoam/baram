#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget


class PanePage(QWidget):
    def __init__(self, ui):
        super().__init__()
        self._ui = ui

    def init(self):
        pass