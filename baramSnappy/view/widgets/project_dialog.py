#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox

from baramSnappy.app import app
from baramSnappy.libbaram.utils import getFit
from .project_dialog_ui import Ui_ProjectSelector
from .project_widget import ProjectWidget

RECENT_PROJECTS_NUMBER = 100


class ProjectDialog(QDialog):
    actionNewSelected = Signal()
    actionOpenSelected = Signal()
    actionProjectSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_ProjectSelector()
        self._ui.setupUi(self)

        self.setWindowIcon(app.properties.icon())
        self.setWindowTitle(f'{app.properties.fullName} Start')

        self._dialog = None
        self._projectDirectory = None

        self._connectSignalsSlots()

        geometry = app.settings.getLastStartWindowGeometry()
        display = app.qApplication.primaryScreen().availableVirtualGeometry()
        fit = getFit(geometry, display)
        self.setGeometry(fit)

    def setRecents(self, paths):
        self._ui.recentCases.clear()

        for i in range(min(RECENT_PROJECTS_NUMBER, len(paths))):
            item = QListWidgetItem()
            widget = ProjectWidget(Path(paths[i]))
            item.setSizeHint(widget.sizeHint())
            self._ui.recentCases.addItem(item)
            self._ui.recentCases.setItemWidget(item, widget)
            widget.removeClicked.connect(self._remove)

    def getProjectDirectory(self):
        return self._projectDirectory

    def _connectSignalsSlots(self):
        self._ui.newCase.clicked.connect(self._new)
        self._ui.open.clicked.connect(self._open)
        self._ui.recentCases.itemClicked.connect(self._openRecentProject)
        self.finished.connect(self._finished)

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
            app.settings.removeProject(selectedPos)

    def _new(self):
        self.actionNewSelected.emit()

    def _open(self):
        self.actionOpenSelected.emit()

    def _openRecentProject(self, item):
        self.actionProjectSelected.emit(self._ui.recentCases.itemWidget(item).getProjectPath())

    def _finished(self, result):
        app.settings.updateLastStartWindowGeometry(self.geometry())
