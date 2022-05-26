#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path

from PySide6.QtWidgets import QDialog, QFileDialog

from .fan_dialog_ui import Ui_FanDialog


class FanDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_FanDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.fanPQCurveFileSelect.clicked.connect(self._selectFanPQCurveFile)

    def _selectFanPQCurveFile(self):
        fileName = QFileDialog.getOpenFileName(self, self.tr("Open CSV File"), "", self.tr("CSV (*.csv)"))
        if fileName[0]:
            self._ui.fanPQCurveFileName.setText(path.basename(fileName[0]))
