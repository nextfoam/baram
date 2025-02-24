#!/usr/bin/env python
# -*- coding: utf-8 -*-


from baramFlow.coredb.contour import Contour
from baramFlow.coredb.visual_reports_db import VisualReportsDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.view.results.results_model.post_field import FIELD_TEXTS
from widgets.async_message_box import AsyncMessageBox

from .contour_dialog import ContourDialog
from .visual_report_widget import VisualReportWidget


class ContourWidget(VisualReportWidget):
    def __init__(self, contour: Contour):
        super().__init__()

        self._contour = contour
        self._dialog = None

        self.load()

    @property
    def name(self):
        return self._contour.name

    def load(self):
        self._ui.name.setText(self._contour.name)

        fieldName = FIELD_TEXTS[self._contour.field]
        self._ui.description.setText(f'Contour of {fieldName} at time {self._contour.time}')

    async def edit(self):
        times = FileSystem.times()
        if self._contour.time not in times:
            if not await AsyncMessageBox().confirm(
                    self,
                    self.tr('Warning'),
                    self.tr('Configured time folder is not in the disk. Time will be reconfigured if you proceed. Proceed?')):
                return

        self._dialog = ContourDialog(self, self._contour, times)
        self._dialog.accepted.connect(self._editAccepted)
        self._dialog.open()

    def _editAccepted(self):
        VisualReportsDB().updateVisualReport(self._contour)
        self.load()

    def delete(self):
        VisualReportsDB().removeVisualReport(self._contour)