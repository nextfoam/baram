#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import uuid4
import qasync

from PySide6.QtWidgets import QListWidgetItem, QMessageBox

from baramFlow.coredb.contour import Contour
from baramFlow.coredb.visual_reports_db import VisualReportsDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.view.results.visual_reports.contour_dialog import ContourDialog
from baramFlow.view.results.visual_reports.contour_widget import ContourWidget
from baramFlow.view.results.visual_reports.visual_report_widget import VisualReportWidget
from baramFlow.view.widgets.content_page import ContentPage

from widgets.async_message_box import AsyncMessageBox

from .visual_reports_page_ui import Ui_VisualReportsPage


class VisualReportsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_VisualReportsPage()
        self._ui.setupUi(self)

        self._report = None
        self._dialog = None

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._openAddContoursDialog)

        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)
        self._ui.delete_.clicked.connect(self._delete)

    def _load(self):
        self._ui.list.clear()

        for s in VisualReportsDB().getVisualReports().values():
            if isinstance(s, Contour):
                self._addItem(ContourWidget(s))

    def _openAddContoursDialog(self):
        uuid = uuid4()
        name = VisualReportsDB().getNewContourName()
        self._report = Contour(uuid=uuid, name=name)
        self._dialog = ContourDialog(self, self._report, FileSystem.times())
        self._dialog.accepted.connect(self._addContours)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _addContours(self):
        await VisualReportsDB().addVisualReport(self._report)

        self._addItem(ContourWidget(self._report))

        self._report = None
        self._dialog = None

    def _addItem(self, widget: VisualReportWidget):
        item = QListWidgetItem()
        item.setSizeHint(widget.size())
        self._ui.list.addItem(item)
        self._ui.list.setItemWidget(item, widget)

    def _itemSelected(self):
        self._ui.edit.setEnabled(True)
        self._ui.delete_.setEnabled(True)

    @qasync.asyncSlot()
    async def _edit(self):
        await self._currentWidget().edit()

    @qasync.asyncSlot()
    async def _delete(self):
        widget = self._currentWidget()
        confirm = await AsyncMessageBox().question(self, self.tr("Remove Visual Report item"),
                                                   self.tr('Remove "{}"?'.format(widget.name)))
        if confirm == QMessageBox.StandardButton.Yes:
            await widget.delete()
            self._ui.list.takeItem(self._ui.list.currentRow())
            if self._ui.list.count() < 1:
                self._ui.edit.setEnabled(False)
                self._ui.delete_.setEnabled(False)

    def _currentWidget(self) -> VisualReportWidget:
        return self._ui.list.itemWidget(self._ui.list.currentItem())

