#!/usr/bin/env python
# -*- coding: utf-8 -*-


import qasync
from PySide6.QtWidgets import QWidget

from baramFlow.base.graphic.graphic import Graphic
from baramFlow.base.graphic.graphics_db import GraphicsDB

from .graphic_dialog import GraphicDialog
from .graphic_widget_ui import Ui_GraphicWidget


class GraphicWidget(QWidget):
    def __init__(self, graphic: Graphic):
        super().__init__()

        self._ui = Ui_GraphicWidget()
        self._ui.setupUi(self)

        self._graphic = graphic
        self._dialog = None

        self.load()

    @property
    def name(self):
        return self._graphic.name

    def load(self):
        self._ui.name.setText(self._graphic.name)

        self._ui.description.setText(f'Colored by {self._graphic.field.text} at time {self._graphic.time}')

    async def edit(self):
        self._dialog = GraphicDialog(self, self._graphic)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _editAccepted(self):
        await self._graphic.notifyReportUpdated()
        self.load()

    async def delete(self):
        await GraphicsDB().removeVisualReport(self._graphic)