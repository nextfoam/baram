#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMainWindow

from view.case_wizard.case_wizard import CaseWizard

from .main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self.connectSignalsSlots()
        self._wizard = None

    def connectSignalsSlots(self):
        self._ui.actionExit.triggered.connect(self.close)
        self._ui.actionNew.triggered.connect(self.openWizard)

    def openWizard(self, signal):
        self._wizard = CaseWizard()

        self._wizard.exec()

