#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QEvent, Signal
from PySide6.QtGui import QEnterEvent, QMouseEvent


class FlatPushButton(QPushButton):
    doubleClicked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlat(True)

    def enterEvent(self, event: QEnterEvent) -> None:
        self.setFlat(False)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.setFlat(True)
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        super().mouseDoubleClickEvent(event)
        self.doubleClicked.emit()
