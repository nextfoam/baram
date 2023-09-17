#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal, QSize
from PySide6.QtWidgets import QPushButton, QSizePolicy
from PySide6.QtGui import QIcon


class IconCheckBox(QPushButton):
    checkStateChanged = Signal(bool)

    def __init__(self, onIconFileName, offIconFileName):
        icon = QIcon()
        icon.addFile(onIconFileName, QSize(), QIcon.Normal, QIcon.On)
        icon.addFile(offIconFileName, QSize(), QIcon.Normal, QIcon.Off)
        super().__init__()

        self.setCheckable(True)
        self.setIcon(icon)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet('border: 0px')
        self.toggled.connect(self._toggled)

    def _toggled(self, checked):
        self.checkStateChanged.emit(checked)
