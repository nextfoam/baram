#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtWidgets import QMenu, QListWidgetItem, QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.view.widgets.content_page import ContentPage
from widgets.async_message_box import AsyncMessageBox
from .monitors_page_ui import Ui_MonitorsPage
from .force_dialog import ForceDialog
from .point_dialog import PointDialog
from .surface_dialog import SurfaceDialog
from .volume_dialog import VolumeDialog
from .monitor_widget import ForceMonitorWidget, PointMonitorWidget, SurfaceMonitorWidget, VolumeMonitorWidget


class MonitorsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MonitorsPage()
        self._ui.setupUi(self)

        self._menu = QMenu()
        self._forcesAdd     = self._menu.addAction(self.tr('&Forces'))
        self._pointsAdd     = self._menu.addAction(self.tr('&Points'))
        self._surfacesAdd   = self._menu.addAction(self.tr('&Surfaces'))
        self._volumesAdd    = self._menu.addAction(self.tr('&Volumes'))
        self._ui.add.setMenu(self._menu)

        self._dialog = None

        self._connectSignalsSlots()
        self._load()

    def _load(self):
        self._ui.list.clear()

        db = coredb.CoreDB()
        for m in db.getForceMonitors():
            self._addItem(ForceMonitorWidget(m))
        for m in db.getPointMonitors():
            self._addItem(PointMonitorWidget(m))
        for m in db.getSurfaceMonitors():
            self._addItem(SurfaceMonitorWidget(m))
        for m in db.getVolumeMonitors():
            self._addItem(VolumeMonitorWidget(m))

    def _connectSignalsSlots(self):
        self._forcesAdd.triggered.connect(self._openForcesAddDialog)
        self._pointsAdd.triggered.connect(self._openPointsAddDialog)
        self._surfacesAdd.triggered.connect(self._openSurfacesAddDialog)
        self._volumesAdd.triggered.connect(self._openVolumesAddDialog)
        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)
        self._ui.delete_.clicked.connect(self._delete)

        MonitorDB.signals.monitorChanged.connect(self._load)

    def _openForcesAddDialog(self):
        self._dialog = ForceDialog(self)
        self._dialog.accepted.connect(self._addForcesMonitor)
        self._dialog.open()

    def _openPointsAddDialog(self):
        self._dialog = PointDialog(self)
        self._dialog.accepted.connect(self._addPointsMonitor)
        self._dialog.open()

    def _openSurfacesAddDialog(self):
        self._dialog = SurfaceDialog(self)
        self._dialog.accepted.connect(self._addSurfacesMonitor)
        self._dialog.open()

    def _openVolumesAddDialog(self):
        self._dialog = VolumeDialog(self)
        self._dialog.accepted.connect(self._addVolumesMonitor)
        self._dialog.open()

    def _addForcesMonitor(self):
        self._addItem(ForceMonitorWidget(self._dialog.getName()))

    def _addPointsMonitor(self):
        self._addItem(PointMonitorWidget(self._dialog.getName()))

    def _addSurfacesMonitor(self):
        self._addItem(SurfaceMonitorWidget(self._dialog.getName()))

    def _addVolumesMonitor(self):
        self._addItem(VolumeMonitorWidget(self._dialog.getName()))

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

    def _currentWidget(self):
        return self._ui.list.itemWidget(self._ui.list.currentItem())
