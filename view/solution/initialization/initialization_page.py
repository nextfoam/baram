#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QMessageBox

from app import app
from coredb import coredb
from coredb.project import Project, SolverStatus
from coredb.region_db import DEFAULT_REGION_NAME
from openfoam.case_generator import CaseGenerator
from openfoam.file_system import FileSystem
from openfoam.run import runParallelUtility
from view.widgets.progress_dialog_simple import ProgressDialogSimple
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

        self._sectionActors = {}

        self._load()

    def _connectSignalsSlots(self):
        self._ui.initialize.clicked.connect(self._initialize)

    def showEvent(self, ev):
        if not ev.spontaneous():
            for i in range(self._ui.tabWidget.count()):
                widget: InitializationWidget = self._ui.tabWidget.widget(i)
                widget.load()

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if not ev.spontaneous():
            view = app.renderingView
            for actor in self._sectionActors.values():
                if actor:
                    view.removeActor(actor)

            view.refresh()
            self._sectionActors = {}

        return super().hideEvent(ev)

    def _load(self):
        regions = self._db.getRegions()
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

    @qasync.asyncSlot()
    async def _initialize(self):
        confirm = QMessageBox.question(self, self.tr("Initialization"), self.tr("All saved data will be deleted. OK?"))
        if confirm == QMessageBox.Yes:
            progressDialog = ProgressDialogSimple(self, self.tr('Case Initialization'))
            progressDialog.open()

            progressDialog.setLabelText('Clean-up Files')

            regions = self._db.getRegions()
            try:
                await FileSystem.initialize(regions)
            except PermissionError:
                progressDialog.finish('Permission error')
                return

            Project.instance().setSolverStatus(SolverStatus.NONE)

            caseGenerator = CaseGenerator()
            caseGenerator.progress.connect(progressDialog.setLabelText)

            try:
                await caseGenerator.setupCase()
            except RuntimeError as e:
                progressDialog.finish(self.tr('Case generation failed. - ') + str(e))
                return

            sectionNames: [str] = self._db.getList(f'.//regions/region/initialization/advanced/sections/section/name')
            if len(sectionNames) > 0:
                progressDialog.setLabelText('Setting Section Values')

                numCores = int(self._db.getValue('.//runCalculation/parallel/numberOfCores'))
                caseRoot = FileSystem.caseRoot()

                proc = await runParallelUtility('setFields', '-writeBoundaryFields', '-case', caseRoot, np=numCores, cwd=caseRoot)
                result = await proc.wait()

                if result != 0:
                    progressDialog.finish(self.tr('Setting Section Values failed.'))
                    return

            progressDialog.finish(self.tr('Initialization Completed'))

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
