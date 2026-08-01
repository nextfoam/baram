#!/usr/bin/env python
# -*- coding: utf-8 -*-

from widgets.rendering.rendering_toolbar import RenderingToolbar

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from vtkmodules.vtkRenderingCore import vtkActor

from .rendering_view_ui import Ui_RenderingView


class RenderingView(QWidget):
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._ui = Ui_RenderingView()
        self._ui.setupUi(self)

        self._view = self._ui.view

        self._toolbar = RenderingToolbar(self._ui, self._view, self)

        # Class name of "RenderingView" is used
        # not to call the method of my children
        # but to call my own method
        RenderingView._connectSignalsSlots(self)

        self._ui.axis.setChecked(True)

    def view(self):
        return self._view

    def close(self):
        self._view.close()
        return super().close()

    def addActor(self, actor: vtkActor):
        self._view.addActor(actor)

    def removeActor(self, actor):
        self._view.removeActor(actor)

    def refresh(self):
        self._view.refresh()

    def fitCamera(self):
        self._view.fitCamera()

    def _connectSignalsSlots(self):
        self._view.viewClosed.connect(self.viewClosed)
