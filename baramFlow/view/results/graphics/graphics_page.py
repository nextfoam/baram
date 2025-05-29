#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import uuid4
import qasync

from PySide6.QtWidgets import QListWidgetItem, QMessageBox

from baramFlow.base.graphic.graphic import Graphic
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB
from baramFlow.base.graphic.graphics_db import GraphicsDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.view.results.graphics.graphic_dialog import GraphicDialog
from baramFlow.view.results.graphics.graphic_widget import GraphicWidget
from baramFlow.view.widgets.content_page import ContentPage

from widgets.async_message_box import AsyncMessageBox

from .graphics_page_ui import Ui_GraphicsPage


class GraphicsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_GraphicsPage()
        self._ui.setupUi(self)

        self._report = None
        self._dialog = None

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._openAddGraphicDialog)

        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)
        self._ui.delete_.clicked.connect(self._delete)

    def _load(self):
        self._ui.list.clear()

        for s in GraphicsDB().getVisualReports().values():
            if isinstance(s, Graphic):
                self._addItem(GraphicWidget(s))

    @qasync.asyncSlot()
    async def _openAddGraphicDialog(self):
        if len(ScaffoldsDB().getScaffolds()) == 0:
            await AsyncMessageBox().warning(self, self.tr('Warning'),
                                            self.tr('There is no Scaffold.\nAt least one scaffold is required to configure Graphics Report'))
            return

        uuid = uuid4()
        name = GraphicsDB().getNewGraphicName()
        self._report = Graphic(uuid=uuid, name=name)
        times = FileSystem.times()
        self._report.time = times[-1]
        self._dialog = GraphicDialog(self, self._report, times)
        self._dialog.accepted.connect(self._addGraphic)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _addGraphic(self):
        await GraphicsDB().addVisualReport(self._report)

        self._addItem(GraphicWidget(self._report))

        self._report = None
        self._dialog = None

    def _addItem(self, widget: GraphicWidget):
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

    def _currentWidget(self) -> GraphicWidget:
        return self._ui.list.itemWidget(self._ui.list.currentItem())

