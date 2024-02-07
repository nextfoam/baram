#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget


class ContentPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

    def save(self):
        return True

    def checkToQuit(self):
        return True
