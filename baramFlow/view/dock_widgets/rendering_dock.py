#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal, QCoreApplication, QEvent, Qt

from PySide6QtAds import CDockWidget

from baramFlow.view.widgets.rendering_view import RenderingView


class RenderingDock(CDockWidget):
    def __init__(self):
        super().__init__(self._title())

        self._widget = RenderingView()
        self.setWidget(self._widget)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(self._title())

        super().changeEvent(event)

    def _title(self):
        return QCoreApplication.translate('RenderingDock', 'Mesh')
