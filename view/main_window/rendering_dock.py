#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .tabified_dock import TabifiedDock
from .rendering_view import RenderingView


class RenderingDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._view = RenderingView(self)
        self.setWidget(self._view)
        self._translate()

    @property
    def view(self):
        return self._view

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def _translate(self):
        self.setWindowTitle(self.tr("Mesh"))

    def close(self):
        self._view.close()

        return super().close()
