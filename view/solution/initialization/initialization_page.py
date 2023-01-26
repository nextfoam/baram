#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.project import Project, SolverStatus
from coredb.region_db import DEFAULT_REGION_NAME
from openfoam.file_system import FileSystem
from view.widgets.progress_dialog import ProgressDialog
from view.widgets.content_page import ContentPage
from .initialization_page_ui import Ui_InitializationPage
from .initialization_widget import InitializationWidget


class InitializationPage(ContentPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_InitializationPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._connectSignalsSlots()

        self.load()

    def _connectSignalsSlots(self):
        self._ui.initialize.clicked.connect(self._initialize)

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        for i in range(self._ui.tabWidget.count()):
            widget: InitializationWidget = self._ui.tabWidget.widget(i)
            widget.load()

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if not ev.spontaneous():
            self.save()

        return super().hideEvent(ev)

    def load(self):
        regions = self._db.getRegions()
        if len(regions) == 1 and not regions[0]:
            widget = InitializationWidget('')
            self._ui.tabWidget.addTab(widget, DEFAULT_REGION_NAME)
        else:
            for rname in regions:
                widget = InitializationWidget(rname)
                self._ui.tabWidget.addTab(widget, rname)

        for i in range(self._ui.tabWidget.count()):
            widget: InitializationWidget = self._ui.tabWidget.widget(i)
            widget.load()

    def clear(self):
        for i in range(self._ui.tabWidget.count()):
            widget: InitializationWidget = self._ui.tabWidget.widget(0)
            self._ui.tabWidget.removeTab(0)
            widget.close()

    def save(self):
        for i in range(self._ui.tabWidget.count()):
            widget: InitializationWidget = self._ui.tabWidget.widget(i)
            if not widget.save():
                return False

        return True

    @qasync.asyncSlot()
    async def _initialize(self):
        confirm = QMessageBox.question(self, self.tr("Initialize"), self.tr("All saved data will be deleted. OK?"))
        if confirm == QMessageBox.Yes:
            progress = ProgressDialog(self, self.tr('Case Initialization'), self.tr('Initializing the case.'))
            regions = self._db.getRegions()
            await FileSystem.initialize(regions)
            Project.instance().setSolverStatus(SolverStatus.NONE)
            progress.close()
