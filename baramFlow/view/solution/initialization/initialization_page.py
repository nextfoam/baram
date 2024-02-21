#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QMessageBox

from libbaram.exception import CanceledException
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME
from baramFlow.openfoam.solver import SolverNotFound
from baramFlow.view.widgets.content_page import ContentPage
from .initialization_page_ui import Ui_InitializationPage
from .initialization_widget import InitializationWidget


class InitializationPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_InitializationPage()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        self._sectionActors = {}
        self._dbConfigCount = None

        self._load()

    def _connectSignalsSlots(self):
        self._ui.initialize.clicked.connect(self._initialize)

    def showEvent(self, ev):
        if not ev.spontaneous():
            for i in range(self._ui.tabWidget.count()):
                widget: InitializationWidget = self._ui.tabWidget.widget(i)
                widget.load()

            self._dbConfigCount = coredb.CoreDB().configCount

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if not ev.spontaneous():
            if app.window:
                view = app.renderingView
                for actor in self._sectionActors.values():
                    if actor:
                        view.removeActor(actor)

                view.refresh()
                self._sectionActors = {}

        return super().hideEvent(ev)

    def _load(self):
        regions = coredb.CoreDB().getRegions()
        if len(regions) == 1 and not regions[0]:
            widget = InitializationWidget('')
            widget.displayChecked.connect(self._showSectionActor)
            widget.displayUnchecked.connect(self._hideSectionActor)
            self._ui.tabWidget.addTab(widget, DEFAULT_REGION_NAME)
        else:
            for rname in regions:
                widget = InitializationWidget(rname)
                widget.displayChecked.connect(self._showSectionActor)
                widget.displayUnchecked.connect(self._hideSectionActor)
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

    def checkToQuit(self):
        if coredb.CoreDB().configCount != self._dbConfigCount:
            confirm = QMessageBox.question(
                self, self.tr("Changed Not Applied"),
                self.tr(
                    'Initialization configuration has changed but "Initialization" button was not clicked. Proceed?'),
                defaultButton=QMessageBox.StandardButton.No)

            if confirm == QMessageBox.StandardButton.No:
                return False

        return True

    @qasync.asyncSlot()
    async def _initialize(self):
        if not self.save():
            return

        confirm = await AsyncMessageBox().question(self, self.tr("Initialization"), self.tr("All saved data will be deleted. OK?"))
        if confirm == QMessageBox.StandardButton.Yes:
            progressDialog = ProgressDialog(self, self.tr('Case Initialization'))
            app.case.progress.connect(progressDialog.setLabelText)
            progressDialog.open()

            try:
                await app.case.initialize()
                progressDialog.finish(self.tr('Initialization Completed'))
                self._dbConfigCount = coredb.CoreDB().configCount
            except PermissionError:
                progressDialog.finish('Permission error')
            except SolverNotFound as e:
                progressDialog.finish(self.tr('Case generating fail. - ') + str(e))
            except CanceledException:
                progressDialog.finish(self.tr('Calculation cancelled'))

    def _showSectionActor(self, section):
        view = app.renderingView

        self._sectionActors[section.key] = section.actor()
        view.addActor(section.actor())
        view.refresh()

    def _hideSectionActor(self, section):
        view = app.renderingView

        if section.key in self._sectionActors and self._sectionActors[section.key]:
            self._sectionActors[section.key] = None
            view.removeActor(section.actor())
            view.refresh()
