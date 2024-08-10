#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramMesh.view.main_window.main_window_ui import Ui_MainWindow
from .ruler_widget import RulerWidget


class RenderingTool:
    def __init__(self, ui: Ui_MainWindow):
        self._ui = ui
        self._view = ui.renderingView

        self._ruler = None

        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.axis.toggled.connect(self._view.setAxisVisible)
        self._ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        self._ui.ruler.toggled.connect(self._setRulerVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.rotate.clicked.connect(self._view.rollCamera)

    def enable(self):
        self._ui.toolbar.setEnabled(True)
        self._ui.renderingView.setEnabled(True)

    def disable(self):
        self.clear()
        self._ui.toolbar.setEnabled(False)
        self._ui.renderingView.setEnabled(False)

    def clear(self):
        self._ui.axis.setChecked(False)
        self._ui.cubeAxis.setChecked(False)

    def _setRulerVisible(self, checked):
        if checked:
            self._ruler = RulerWidget(self._view.interactor(), self._view.renderer())
            self._ruler.on()
        else:
            self._ruler.off()
            self._ruler = None
