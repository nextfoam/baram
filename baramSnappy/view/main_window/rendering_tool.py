#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramSnappy.view.main_window.main_window_ui import Ui_MainWindow


class RenderingTool:
    def __init__(self, ui: Ui_MainWindow):
        self._ui = ui
        self._view = ui.renderingView

        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.axis.toggled.connect(self._view.setAxisVisible)
        self._ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.rotate.clicked.connect(self._view.rollCamera)

    def clear(self):
        self._ui.axis.setChecked(False)
        self._ui.cubeAxis.setChecked(False)
