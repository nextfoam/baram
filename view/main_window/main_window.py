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
        self._ui.editList.itemDoubleClicked.connect(self.listPageItemEdit)
        self._ui.edit.clicked.connect(self.listPageItemEdit)

    def openWizard(self, signal):
        self._wizard = CaseWizard()

        self._wizard.exec()

    def changeForm(self, current, previous):
        if previous is not None:
            previousPane = self._menuView.paneOf(previous)
            previousPane.save()

        currentPane = self._menuView.paneOf(current)
        if currentPane.index < 0:
            currentPane.index = self._formView.addPage(currentPane)

        currentPane.init()
        currentPane.load()
        self._formView.changePane(currentPane.index)

    def listPageItemEdit(self):
        currentPane = self._menuView.currentPane()
        currentPane.edit()
        pass

