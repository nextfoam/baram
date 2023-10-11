#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QDialog


class ResizableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

    def event(self, ev):
        if ev.type() == QEvent.LayoutRequest:
            QTimer.singleShot(0, self.adjustSize)
        return super().event(ev)
