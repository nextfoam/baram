#!/usr/bin/env python
# -*- coding: utf-8 -*-

from widgets.rendering.rendering_toolbar import RenderingToolbar
from widgets.rendering.rendering_widget import RenderingWidget

from baramMesh.app import app
from baramMesh.view.main_window.main_window_ui import Ui_MainWindow


class RenderingTool:
    def __init__(self, ui: Ui_MainWindow):
        self._ui = ui
        self._view: RenderingWidget = ui.renderingView

        self._toolbar = RenderingToolbar(ui, self._view, app.window)

    def enable(self):
        self._ui.toolbar.setEnabled(True)
        self._ui.renderingView.setEnabled(True)

    def disable(self):
        self.clear()
        self._ui.toolbar.setEnabled(False)
        self._ui.renderingView.setEnabled(False)

    def clear(self):
        self._ui.axis.setChecked(True)
        self._ui.cubeAxis.setChecked(False)
