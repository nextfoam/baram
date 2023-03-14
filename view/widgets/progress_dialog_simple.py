#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt, Signal

from .progress_dialog_ui import Ui_ProgressDialog


class ProgressDialogSimple(QDialog):
    cancelClicked = Signal()

    def __init__(self, parent, title: str, cancelable: bool = False):
        super().__init__(parent)
        self._ui = Ui_ProgressDialog()
        self._ui.setupUi(self)

        self._process = None
        self._slot = None
        self._canceled = False

        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        self._ui.button.setVisible(cancelable)

        self._ui.button.clicked.connect(self._cancelClicked)

    def isCanceled(self):
        return self._canceled

    def setLabelText(self, text: str):
        self._ui.label.setText(text)

    def showCancelButton(self, text='Cancel'):
        self._ui.button.setText(text)
        self._ui.button.setVisible(True)

    def hideCancelButton(self):
        self._ui.button.setVisible(False)

    def finish(self, text: str):
        self._ui.label.setText(text)
        self._ui.button.setText(self.tr('Close'))
        self._ui.progressBar.hide()
        self._ui.button.show()

        self._ui.button.clicked.connect(self.close)

    def cancel(self):
        self.close()

    def _cancelClicked(self):
        self.cancelClicked.emit()
        self._canceled = True
        self.close()

