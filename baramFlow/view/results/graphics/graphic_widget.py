#!/usr/bin/env python
# -*- coding: utf-8 -*-


import qasync
from PySide6.QtWidgets import QWidget

from baramFlow.base.graphic.graphic import Graphic
from baramFlow.base.graphic.graphics_db import GraphicsDB
from baramFlow.openfoam.file_system import FileSystem
from widgets.async_message_box import AsyncMessageBox

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
        times = FileSystem.times()
        if self._graphic.time not in times:
            if not await AsyncMessageBox().confirm(
                    self,
                    self.tr('Warning'),
                    self.tr('Configured time folder is not in the file system. Time will be reconfigured if you proceed. Proceed?')):
                return

        self._dialog = GraphicDialog(self, self._graphic, times)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _editAccepted(self):
        await self._graphic.notifyReportUpdated()
        self.load()

    async def delete(self):
        await GraphicsDB().removeVisualReport(self._graphic)