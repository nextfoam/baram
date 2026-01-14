#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QVBoxLayout

from widgets.new_project_widget import NewProjectWidget

from baramMesh.app import app
from .export_dialog_ui import Ui_ExportDialog


class ExportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ExportDialog()
        self._ui.setupUi(self)

        self._pathWidget = NewProjectWidget(self._ui.path, suffix=app.properties.exportSuffix)

        self._ui.ok.setEnabled(False)

        layout = QVBoxLayout(self._ui.path)
        layout.addWidget(self._pathWidget)
        self._pathWidget.hideValidationMessage()

        self.resize(500, self.size().height())

        self._connectSignalsSlots()

    def projectPath(self):
        return self._pathWidget.projectPath()

    def isRunBaramFlowChecked(self):
        return self._ui.run.isChecked()

    def _connectSignalsSlots(self):
        self._pathWidget.pathChanged.connect(self._pathChanged)

    def _pathChanged(self, path):
        self._ui.ok.setEnabled(path is not None)
