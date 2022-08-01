#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path

from PySide6.QtWidgets import QWizardPage, QFileDialog

from coredb.settings import AppSettings
from .workspace_page_ui import Ui_WorkspacePage


class WorkspacePage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(WorkspacePage, self).__init__(*args, **kwargs)

        self._ui = Ui_WorkspacePage()
        self._ui.setupUi(self)

        self._complete = False
        self._locationParent = AppSettings.getRecentDirectory()
        self._updateProjectLocation()

        self.registerField('projectName*', self._ui.projectName)
        self.registerField('projectLocation', self._ui.projectLocation)

        self._connectSignalsSlots()

    def isComplete(self):
        # complete = super().isComplete()
        # if complete:
        complete = True

        if not path.exists(self._locationParent):
            self._ui.validationMessage.setText(self.tr(f'{self._locationParent} is not a directory.'))
            complete = False
        elif not self._ui.projectName.text():
            self._ui.validationMessage.clear()
            complete = False
        elif path.exists(self._ui.projectLocation.text()):
            self._ui.validationMessage.setText(self.tr(f'{self._ui.projectLocation.text()} already exists.'))
            complete = False
        else:
            self._ui.validationMessage.clear()

        if complete != self._complete:
            self._complete = complete
            self.completeChanged.emit()

        return complete

    def _connectSignalsSlots(self):
        self._ui.projectName.textChanged.connect(self._updateProjectLocation)
        self._ui.select.clicked.connect(self._selectLocation)

    def _selectLocation(self):
        dirName = QFileDialog.getExistingDirectory(self, self.tr('Case Directory'), self._locationParent)
        if dirName:
            self._locationParent = dirName
            self._updateProjectLocation()
            self.isComplete()

    def _updateProjectLocation(self):
        self._ui.projectLocation.setText(path.join(self._locationParent, self._ui.projectName.text()))
