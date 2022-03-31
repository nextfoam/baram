#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMainWindow

from view.case_wizard.case_wizard import CaseWizard
from .form_view import FormView
from .main_window_ui import Ui_MainWindow
from .menu_view import MenuView


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self._wizard = None

        self._menuView = MenuView(self._ui.menuView)
        self._formView = FormView(self._ui.formView, self._ui)

        self.connectSignalsSlots()

    def connectSignalsSlots(self):
        self._ui.actionExit.triggered.connect(self.close)
        self._ui.actionNew.triggered.connect(self.openWizard)
        self._menuView.connectCurrentItemChanged(self.changeForm)

    def openWizard(self, signal):
        self._wizard = CaseWizard()

        self._wizard.exec()

    def changeForm(self, current, previous):
        if previous is not None:
            previousPane = self._menuView.paneOf(previous).pane
            previousPane.save()

        currentPane = self._menuView.paneOf(current).pane
        if currentPane.index < 0:
            currentPane.index = self._formView.addPage(currentPane.create_page())
        else:
            self._formView.initPage(currentPane.index)

        page = self._formView.page(currentPane.index)
        currentPane.load(page)
        self._formView.changePane(currentPane.index)
