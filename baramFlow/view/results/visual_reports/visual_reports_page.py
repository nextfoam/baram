#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QVBoxLayout, QMenu, QListWidgetItem, QMessageBox

from PySide6QtAds import DockWidgetArea, CDockManager, CDockWidget


from baramFlow.view.results.visual_reports.contour_dialog import ContoursDialog
from baramFlow.view.results.visual_reports.visual_report_widget import ContoursWidget
from baramFlow.view.widgets.content_page import ContentPage

from widgets.async_message_box import AsyncMessageBox

from .rendering_view import RenderingDock

from .graphics_page_ui import Ui_GraphicsPage


class VisualReportsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_GraphicsPage()
        self._ui.setupUi(self)

        self._menu = QMenu()
        self._addCoutours: QAction    = self._menu.addAction(self.tr('&Contours'))
        self._addVectors: QAction     = self._menu.addAction(self.tr('&Vectors'))
        self._addPathlines: QAction   = self._menu.addAction(self.tr('&Pathlines'))
        self._addParticleTracks: QAction    = self._menu.addAction(self.tr('&Particle Tracks'))
        self._ui.add.setMenu(self._menu)

        self._dialog = None

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._addCoutours.triggered.connect(self._openAddContoursDialog)
        self._addVectors.triggered.connect(self._openAddVectorsDialog)
        self._addPathlines.triggered.connect(self._openAddPathlinesDialog)
        self._addParticleTracks.triggered.connect(self._openAddParticleTracksDialog)
        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)
        self._ui.delete_.clicked.connect(self._delete)

    def _openAddContoursDialog(self):
        self._dialog = ContoursDialog(self)
        self._dialog.accepted.connect(self._addContours)
        self._dialog.open()

    def _openAddVectorsDialog(self):
        pass

    def _openAddPathlinesDialog(self):
        pass

    def _openAddParticleTracksDialog(self):
        pass

    def _addContours(self):
        self._addItem(ContoursWidget(self._dialog.getName()))


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
        widget = self._currentWidget()
        confirm = await AsyncMessageBox().question(self, self.tr("Remove monitor item"),
                                                   self.tr('Remove "{}"?'.format(widget.name)))
        if confirm == QMessageBox.StandardButton.Yes:
            widget.delete()
            self._ui.list.takeItem(self._ui.list.currentRow())