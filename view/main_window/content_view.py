#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QVBoxLayout

from view.geometry.geometry_page import GeometryPage
# from view.region.region_page import RegionPage
from .naviagtion_view import Step


pageCreator = {
    Step.NONE: None,
    Step.GEOMETRY: GeometryPage,
    # Step.REGION: RegionPage,
    Step.BASE_GRID: None,
    Step.CASTELLATION: None,
    Step.SNAP: None,
    Step.BOUNDARY_LAYER: None,
    Step.REFINEMENT: None,
}


class ContentView:
    def __init__(self, ui):
        super().__init__()
        self._view = ui.content

        self._view.setLayout(QVBoxLayout())
        self._view.layout().setContentsMargins(0, 0, 0, 0)

    def moveToStep(self, step):
        if item := self._view.layout().takeAt(0):
            item.widget().deleteLater()

        if creator := pageCreator[step]:
            page = creator()
            self._view.layout().addWidget(page)
