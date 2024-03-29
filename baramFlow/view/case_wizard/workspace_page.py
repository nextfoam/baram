#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtWidgets import QWizardPage, QFileDialog

from baramFlow.coredb.app_settings import AppSettings
from .workspace_page_ui import Ui_WorkspacePage


class WorkspacePage(QWizardPage):
    def __init__(self, parent, path=None):
        super(WorkspacePage, self).__init__(parent)

        self._ui = Ui_WorkspacePage()
        self._ui.setupUi(self)

        self._complete = False
        self._locationParent = None
        self._meshProject = False

        if path is None:
            self._locationParent = Path(AppSettings.getRecentLocation()).resolve()
            self._updateProjectLocation()
        else:
            self._meshProject = True
            self._locationParent = path.parent
            self._ui.projectName.setText(path.name)
            self._updateProjectLocation()
            self._ui.workspace.setEnabled(False)

        self.registerField('projectName*', self._ui.projectName)
        self.registerField('projectLocation', self._ui.projectLocation)

        self._dialog = None

        self._connectSignalsSlots()

    def isComplete(self):
        if self._meshProject:
            return True

        complete = False

        if not self._locationParent.exists():
            self._ui.validationMessage.setText(self.tr(f'{self._locationParent} is not a directory.'))
        elif not self._ui.projectName.text():
            self._ui.validationMessage.clear()
        elif Path(self._ui.projectLocation.text()).exists():
            self._ui.validationMessage.setText(self.tr(f'{self._ui.projectLocation.text()} already exists.'))
        else:
            complete = True
            self._ui.validationMessage.clear()

        if complete != self._complete:
            self._complete = complete
            self.completeChanged.emit()

        return complete

    def _connectSignalsSlots(self):
        self._ui.projectName.textChanged.connect(self._updateProjectLocation)
        self._ui.select.clicked.connect(self._selectLocation)

    def _selectLocation(self):
        self._dialog = QFileDialog(self, self.tr('Select Location'), str(self._locationParent))
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.accepted.connect(self._locationParentSelected)
        self._dialog.open()

    def _updateProjectLocation(self):
        self._ui.projectLocation.setText(str(self._locationParent / self._ui.projectName.text()))

    def _locationParentSelected(self):
        if dirs := self._dialog.selectedFiles():
            self._locationParent = Path(dirs[0]).resolve()
            self._updateProjectLocation()
            self.isComplete()
