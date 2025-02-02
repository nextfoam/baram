#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import uuid4
import qasync

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QListWidgetItem, QMessageBox

from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.view.results.scaffolds.ios_surface_dialog import IsoSurfaceDialog
from baramFlow.view.results.scaffolds.scaffold_widget import IsoSurfaceWidget, ScaffoldWidget
from baramFlow.view.widgets.content_page import ContentPage

from widgets.async_message_box import AsyncMessageBox

from .scaffolds_page_ui import Ui_ScaffoldsPage


class ScaffoldsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_ScaffoldsPage()
        self._ui.setupUi(self)

        self._menu = QMenu()

        self._addIsoSurfaceMenu: QAction = self._menu.addAction(self.tr('&Iso Surface'))
        self._addPlaneMenu: QAction      = self._menu.addAction(self.tr('&Plane'))

        self._ui.add.setMenu(self._menu)

        self._scaffold = None
        self._dialog = None

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._addIsoSurfaceMenu.triggered.connect(self._openAddIsoSurfaceDialog)
        self._addPlaneMenu.triggered.connect(self._openAddPlaneDialog)

        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)
        self._ui.delete_.clicked.connect(self._delete)

    def _load(self):
        self._ui.list.clear()

        for s in ScaffoldsDB().getScaffolds().values():
            if isinstance(s, IsoSurface):
                self._addItem(IsoSurfaceWidget(s))

    def _openAddIsoSurfaceDialog(self):
        uuid = uuid4()
        name = ScaffoldsDB().getNewIsoSurfaceName()
        self._scaffold = IsoSurface(uuid=uuid, name=name)
        self._dialog = IsoSurfaceDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._addIsoSurface)
        self._dialog.open()

    def _openAddPlaneDialog(self):
        pass

    def _addIsoSurface(self):
        ScaffoldsDB().addScaffold(self._scaffold)

        self._addItem(IsoSurfaceWidget(self._scaffold))

        self._scaffold = None
        self._dialog = None

    def _addItem(self, widget):
        item = QListWidgetItem()
        item.setSizeHint(widget.size())
        self._ui.list.addItem(item)
        self._ui.list.setItemWidget(item, widget)

    def _removeItem(self, row):
        self._ui.list.takeItem(row)

    def _itemSelected(self):
        self._ui.edit.setEnabled(True)
        self._ui.delete_.setEnabled(True)

    def _edit(self):
        self._currentWidget().edit()

    @qasync.asyncSlot()
    async def _delete(self):
        widget: ScaffoldWidget = self._currentWidget()
        confirm = await AsyncMessageBox().question(self, self.tr("Remove Scaffold item"),
                                                   self.tr('Remove "{}"?'.format(widget.name)))
        if confirm == QMessageBox.StandardButton.Yes:
            ScaffoldsDB().removeScaffold(widget.scaffold)
            self._ui.list.takeItem(self._ui.list.currentRow())

    def _currentWidget(self):
        return self._ui.list.itemWidget(self._ui.list.currentItem())