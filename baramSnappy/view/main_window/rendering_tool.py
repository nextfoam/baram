#!/usr/bin/env python
# -*- coding: utf-8 -*-
from baramSnappy.view.main_window.main_window_ui import Ui_MainWindow


class RenderingTool:
    def __init__(self, ui: Ui_MainWindow):

        self._view = ui.renderingView

        ui.alignAxis.clicked.connect(self._view.alignCamera)
        ui.axis.toggled.connect(self._view.setAxisVisible)
        ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        ui.fit.clicked.connect(self._view.fitCamera)
        ui.perspective.toggled.connect(self._view.setParallelProjection)
        ui.rotate.clicked.connect(self._view.rollCamera)
