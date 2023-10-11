#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QListWidgetItem, QFileDialog, QMessageBox

from libbaram.utils import getFit

from baramFlow.app import app
from baramFlow.coredb.app_settings import AppSettings
from baramFlow.coredb.project_settings import ProjectSettings
from .project_selector_ui import Ui_ProjectSelector
from .project_widget import ProjectWidget

RECENT_PROJECTS_NUMBER = 100


class ProjectSelector(QDialog):
    actionNewSelected = Signal()
    projectSelected = Signal(str)

    def __init__(self):
        super().__init__()
        self._ui = Ui_ProjectSelector()
        self._ui.setupUi(self)

        self.setWindowIcon(app.properties.icon())
        self.setWindowTitle(f'{app.properties.fullName} Start')

        self._dialog = None
        self._projectDirectory = None
        # self.pathItem = []

        self._setupRecentCases()

        geometry = AppSettings.getLastStartWindowGeometry()
        display = app.qApplication.primaryScreen().availableVirtualGeometry()
        fit = getFit(geometry, display)
        self.setGeometry(fit)

        self._connectSignalsSlots()

    def getProjectDirectory(self):
        return self._projectDirectory

    def _finished(self, result):
        AppSettings.updateLastStartWindowGeometry(self.geometry())

    def _connectSignalsSlots(self):
        self.finished.connect(self._finished)

        self._ui.newCase.clicked.connect(self._new)
        self._ui.open.clicked.connect(self._open)
        self._ui.recentCases.itemClicked.connect(self._openRecentProject)

    def _setupRecentCases(self):
        recentCases = AppSettings.getRecentProjects(RECENT_PROJECTS_NUMBER)
        # self.pathItem = []

        for uuid_ in recentCases:
            settings = ProjectSettings()
            if settings.load(uuid_):
                # self.pathItem.append(QListWidgetItem())
                # widget = ProjectWidget(settings)
                # self.pathItem[-1].setSizeHint(widget.sizeHint())
                # self._ui.recentCases.addItem(self.pathItem[-1])
                # self._ui.recentCases.setItemWidget(self.pathItem[-1], widget)
                item = QListWidgetItem()
                widget = ProjectWidget(settings)
                item.setSizeHint(widget.sizeHint())
                self._ui.recentCases.addItem(item)
                self._ui.recentCases.setItemWidget(item, widget)
                widget.removeClicked.connect(self._remove)

    def _remove(self):
        widget = self.sender()

        path = widget.getProjectPath()
        total = self._ui.recentCases.count()
        selectedPos = -1

        for i in range(total):
            item = self._ui.recentCases.item(i)
            if widget == self._ui.recentCases.itemWidget(item):
                selectedPos = i

        msgBox = QMessageBox()
        msgBox.setWindowTitle(self.tr("Remove from list"))
        msgBox.setText(self.tr(f"Do you want to remove selected path from list?\n{path}"))
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Yes)

        result = msgBox.exec()
        if result == QMessageBox.Yes:
            self._ui.recentCases.takeItem(selectedPos)
            # del self.pathItem[selectedPos]
            AppSettings.removeProject(selectedPos)

    def _new(self):
        self.actionNewSelected.emit()

    def _open(self):
        self._dialog = QFileDialog(self, self.tr('Select Project Directory'), AppSettings.getRecentLocation())
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self.projectSelected)
        self._dialog.open()

    def _openRecentProject(self, item):
        self.projectSelected.emit(self._ui.recentCases.itemWidget(item).getProjectPath())
