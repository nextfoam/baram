#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage, QFileDialog

from .workspace_page_ui import Ui_WorkspacePage


class WorkspacePage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(WorkspacePage, self).__init__(*args, **kwargs)

        self._ui = Ui_WorkspacePage()
        self._ui.setupUi(self)

        self.registerField('workingDirectory*', self._ui.workingDirectory)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.workingDirectorySelect.clicked.connect(self._selectWorkingDirectory)

    def _selectWorkingDirectory(self):
        dirName = QFileDialog.getExistingDirectory(self)
        if dirName:
            self._ui.workingDirectory.setText(dirName)
