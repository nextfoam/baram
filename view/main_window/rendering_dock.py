#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import app
from .tabified_dock import TabifiedDock
from .rendering_view import RenderingView


class RenderingDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._view = RenderingView(self)
        self.setWidget(self._view)
        self._translate()

        parent.windowClosed.connect(self._mainWindowClosed)

    @property
    def view(self):
        return self._view

    def closeEvent(self, event):
        if app.closed():
            event.accept()
        else:
            self.hide()
            event.ignore()

    def _translate(self):
        self.setWindowTitle(self.tr("Mesh"))

    def _mainWindowClosed(self):
        self._view.close()
