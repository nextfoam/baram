#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QVBoxLayout

from .naviagtion_view import Step
from view.geometry.geometry_page import GeometryPage


pageCreator = {
    Step.NONE: None,
    Step.GEOMETRY: GeometryPage,
    Step.BASE_GRID: None,
    Step.CASTELLATION: None,
    Step.SNAP: None,
    Step.BOUNDARY_LAYER: None,
    Step.REFINEMENT: None,
}


class ContentView:
    def __init__(self, ui):
        super().__init__()
        self._titleBar = ui.title
        self._view = ui.content

        self._view.setLayout(QVBoxLayout())
        self._view.layout().setContentsMargins(0, 0, 0, 0)

    def moveToStep(self, step):
        if item := self._view.layout().takeAt(0):
            item.widget().deleteLater()
            self._titleBar.setText('')

        if creator := pageCreator[step]:
            page = creator()
            self._view.layout().addWidget(page)
            self._titleBar.setText(page.title())
