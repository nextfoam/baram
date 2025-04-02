#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import uuid4
import qasync

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QListWidgetItem, QMessageBox

from baramFlow.coredb.boundary_scaffold import BoundaryScaffold
from baramFlow.coredb.disk_scaffold import DiskScaffold
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.line_scaffold import LineScaffold
from baramFlow.coredb.parallelogram import Parallelogram
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.coredb.sphere_scaffold import SphereScaffold
from baramFlow.view.results.scaffolds.boundary_scaffold_dialog import BoundaryScaffoldDialog
from baramFlow.view.results.scaffolds.disk_scaffold_dialog import DiskScaffoldDialog
from baramFlow.view.results.scaffolds.iso_surface_dialog import IsoSurfaceDialog
from baramFlow.view.results.scaffolds.line_scaffold_dialog import LineScaffoldDialog
from baramFlow.view.results.scaffolds.parallelogram_dialog import ParallelogramDialog
from baramFlow.view.results.scaffolds.scaffold_widget import BoundaryScaffoldWidget, DiskScaffoldWidget, IsoSurfaceWidget, LineScaffoldWidget, ParallelogramWidget, ScaffoldWidget, SphereScaffoldWidget
from baramFlow.view.results.scaffolds.sphere_scaffold_dialog import SphereScaffoldDialog
from baramFlow.view.widgets.content_page import ContentPage

from widgets.async_message_box import AsyncMessageBox

from .scaffolds_page_ui import Ui_ScaffoldsPage


class ScaffoldsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_ScaffoldsPage()
        self._ui.setupUi(self)

        self._menu = QMenu()

        self._addBoundaryScaffoldMenu: QAction   = self._menu.addAction(self.tr('&Boundary'))
        self._addIsoSurfaceMenu: QAction         = self._menu.addAction(self.tr('&Iso Surface'))
        self._addPlaneMenu: QAction              = self._menu.addAction(self.tr('&Plane'))
        self._addDIskScaffoldMenu: QAction       = self._menu.addAction(self.tr('&Disk'))
        self._addLineScaffoldMenu: QAction       = self._menu.addAction(self.tr('&Line'))
        self._addParallelogramMenu: QAction      = self._menu.addAction(self.tr('&Parallelogram'))
        self._addSphereScaffoldMenu: QAction     = self._menu.addAction(self.tr('&Sphere'))

        self._ui.add.setMenu(self._menu)

        self._scaffold = None
        self._dialog = None

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._addBoundaryScaffoldMenu.triggered.connect(self._openAddBoundaryScaffoldDialog)
        self._addIsoSurfaceMenu.triggered.connect(self._openAddIsoSurfaceDialog)
        self._addPlaneMenu.triggered.connect(self._openAddPlaneDialog)
        self._addDIskScaffoldMenu.triggered.connect(self._openDiskScaffoldDialog)
        self._addLineScaffoldMenu.triggered.connect(self._openLineScaffoldDialog)
        self._addParallelogramMenu.triggered.connect(self._openParallelogramDialog)
        self._addSphereScaffoldMenu.triggered.connect(self._openSphereScaffoldDialog)

        self._ui.list.currentItemChanged.connect(self._itemSelected)
        self._ui.list.itemDoubleClicked.connect(self._edit)
        self._ui.edit.clicked.connect(self._edit)
        self._ui.delete_.clicked.connect(self._delete)

    def _load(self):
        self._ui.list.clear()

        for s in ScaffoldsDB().getScaffolds().values():
            if isinstance(s, BoundaryScaffold):
                self._addItem(BoundaryScaffoldWidget(s))
            elif isinstance(s, IsoSurface):
                self._addItem(IsoSurfaceWidget(s))
            elif isinstance(s, DiskScaffold):
                self._addItem(DiskScaffoldWidget(s))
            elif isinstance(s, LineScaffold):
                self._addItem(LineScaffoldWidget(s))
            elif isinstance(s, Parallelogram):
                self._addItem(ParallelogramWidget(s))
            elif isinstance(s, SphereScaffold):
                self._addItem(SphereScaffoldWidget(s))

    def _openAddBoundaryScaffoldDialog(self):
        uuid = uuid4()
        name = ScaffoldsDB().getNewBoundaryScaffoldName()
        self._scaffold = BoundaryScaffold(uuid=uuid, name=name)
        self._dialog = BoundaryScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._addBoundaryScaffold)
        self._dialog.open()

    def _openAddIsoSurfaceDialog(self):
        uuid = uuid4()
        name = ScaffoldsDB().getNewIsoSurfaceName()
        self._scaffold = IsoSurface(uuid=uuid, name=name)
        self._dialog = IsoSurfaceDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._addIsoSurface)
        self._dialog.open()

    def _openAddPlaneDialog(self):
        pass

    def _openDiskScaffoldDialog(self):
        uuid = uuid4()
        name = ScaffoldsDB().getNewDiskName()
        self._scaffold = DiskScaffold(uuid=uuid, name=name)
        self._dialog = DiskScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._addDiskScaffold)
        self._dialog.open()

    def _openLineScaffoldDialog(self):
        uuid = uuid4()
        name = ScaffoldsDB().getNewLineName()
        self._scaffold = LineScaffold(uuid=uuid, name=name)
        self._dialog = LineScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._addLineScaffold)
        self._dialog.open()

    def _openParallelogramDialog(self):
        uuid = uuid4()
        name = ScaffoldsDB().getNewLineName()
        self._scaffold = Parallelogram(uuid=uuid, name=name)
        self._dialog = ParallelogramDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._addParallelogram)
        self._dialog.open()

    def _openSphereScaffoldDialog(self):
        uuid = uuid4()
        name = ScaffoldsDB().getNewSphereName()
        self._scaffold = SphereScaffold(uuid=uuid, name=name)
        self._dialog = SphereScaffoldDialog(self, self._scaffold)
        self._dialog.accepted.connect(self._addSphereScaffold)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _addBoundaryScaffold(self):
        await ScaffoldsDB().addScaffold(self._scaffold)

        self._addItem(BoundaryScaffoldWidget(self._scaffold))

        self._scaffold = None
        self._dialog = None

    @qasync.asyncSlot()
    async def _addIsoSurface(self):
        await ScaffoldsDB().addScaffold(self._scaffold)

        self._addItem(IsoSurfaceWidget(self._scaffold))

        self._scaffold = None
        self._dialog = None

    @qasync.asyncSlot()
    async def _addDiskScaffold(self):
        await ScaffoldsDB().addScaffold(self._scaffold)

        self._addItem(DiskScaffoldWidget(self._scaffold))

        self._scaffold = None
        self._dialog = None

    @qasync.asyncSlot()
    async def _addLineScaffold(self):
        await ScaffoldsDB().addScaffold(self._scaffold)

        self._addItem(LineScaffoldWidget(self._scaffold))

        self._scaffold = None
        self._dialog = None

    @qasync.asyncSlot()
    async def _addParallelogram(self):
        await ScaffoldsDB().addScaffold(self._scaffold)

        self._addItem(ParallelogramWidget(self._scaffold))

        self._scaffold = None
        self._dialog = None

    @qasync.asyncSlot()
    async def _addSphereScaffold(self):
        await ScaffoldsDB().addScaffold(self._scaffold)

        self._addItem(SphereScaffoldWidget(self._scaffold))

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
        widget: ScaffoldWidget = self._currentWidget()
        widget.edit()

    @qasync.asyncSlot()
    async def _delete(self):
        widget: ScaffoldWidget = self._currentWidget()
        confirm = await AsyncMessageBox().question(self, self.tr("Remove Scaffold item"),
                                                   self.tr('Remove "{}"?'.format(widget.name)))
        if confirm == QMessageBox.StandardButton.Yes:
            await widget.delete()
            self._ui.list.takeItem(self._ui.list.currentRow())

    def _currentWidget(self):
        return self._ui.list.itemWidget(self._ui.list.currentItem())