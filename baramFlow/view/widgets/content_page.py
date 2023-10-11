#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget


class ContentPage(QWidget):
    def __init__(self):
        super().__init__()

    def save(self):
        return True
