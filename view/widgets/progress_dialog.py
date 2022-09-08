#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt

from .progress_dialog_ui import Ui_ProgressDialog


class ProgressDialog(QDialog):
    def __init__(self, parent, title, label=''):
        super().__init__(parent)
        self._ui = Ui_ProgressDialog()
        self._ui.setupUi(self)

        self._process = None
        self._slot = None
        self._canceled = False

        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self._ui.label.setText(label)

        self._ui.button.hide()

        self._connectSignalsSlots()

        self.show()

    def setProcess(self, proc, text=None, buttontext=None):
        if text:
            self._ui.label.setText(text)
        self._process = proc
        self.setButtonToCancel(self._process.terminate, buttontext)

    def setText(self, text):
        self._ui.label.setText(text)

    def setButtonToCancel(self, slot, text=None):
        if text:
            self._ui.button.setText(text)
        self._slot = slot
        self._ui.button.show()

    def finish(self, text):
        self._process = None
        self._setButtonToClose(text)

    def error(self, text):
        self._setButtonToClose(text)

    def canceled(self):
        return self._canceled

    def _connectSignalsSlots(self):
        self._ui.button.clicked.connect(self._buttonClicked)

    def _setButtonToClose(self, message):
        self._ui.label.setText(message)
        self._ui.button.setText(self.tr('Close'))
        self._ui.progressBar.hide()
        self._ui.button.show()
        self._slot = self.close
        self._canceled = False

    def _buttonClicked(self):
        if self._slot:
            self._canceled = True
            self._slot()

        self.close()
