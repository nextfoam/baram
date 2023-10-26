#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QMessageBox

from libbaram.run import runParallelUtility
from widgets.progress_dialog import ProgressDialog

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project, SolverStatus
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME
from baramFlow.openfoam import parallel
from baramFlow.openfoam.case_generator import CaseGenerator
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.view.widgets.content_page import ContentPage
from .initialization_page_ui import Ui_InitializationPage
from .initialization_widget import InitializationWidget


class InitializationPage(ContentPage):
    def __init__(self):
        super().__init__()
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

        confirm = QMessageBox.question(self, self.tr("Initialization"), self.tr("All saved data will be deleted. OK?"))
        if confirm == QMessageBox.StandardButton.Yes:
            progressDialog = ProgressDialog(self, self.tr('Case Initialization'))
            progressDialog.open()

            progressDialog.setLabelText('Clean-up Files')

            try:
                await FileSystem.initialize()
            except PermissionError:
                progressDialog.finish('Permission error')
                return

            Project.instance().setSolverStatus(SolverStatus.NONE)

            caseGenerator = CaseGenerator()
            caseGenerator.progress.connect(progressDialog.setLabelText)

            progressDialog.showCancelButton()
            progressDialog.cancelClicked.connect(caseGenerator.cancel)
            progressDialog.open()

            try:
                cancelled = await caseGenerator.setupCase()
                if cancelled:
                    progressDialog.finish(self.tr('Initialization cancelled'))
                    return
            except RuntimeError as e:
                progressDialog.finish(self.tr('Case generation failed. - ') + str(e))
                return

            progressDialog.hideCancelButton()

            sectionNames: [str] = coredb.CoreDB().getList(
                f'.//regions/region/initialization/advanced/sections/section/name')
            if len(sectionNames) > 0:
                progressDialog.setLabelText('Setting Section Values')

                caseRoot = FileSystem.caseRoot()
                proc = await runParallelUtility('setFields', '-writeBoundaryFields', '-case', caseRoot,
                                                parallel=parallel.getEnvironment(), cwd=caseRoot)
                result = await proc.wait()

                if result != 0:
                    progressDialog.finish(self.tr('Setting Section Values failed.'))
                    return

            progressDialog.finish(self.tr('Initialization Completed'))
            self._dbConfigCount = coredb.CoreDB().configCount

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
