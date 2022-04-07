#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog


class ResizableDialog(QDialog):
    def __init__(self):
        super().__init__()

    def _setVisible(self, widgetList, visible):
        for widget in widgetList:
            widget.setVisible(visible)

    def _resizeDialog(self, widget):
        while widget is not None:
            widget.adjustSize()
            widget = widget.parent()


