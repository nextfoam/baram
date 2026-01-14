#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QTimer, Qt, Signal

from .progress_dialog_ui import Ui_ProgressDialog


class ProgressDialog(QDialog):
    cancelClicked = Signal()

    def __init__(self, parent, title: str, cancelable: bool = False, autoCloseOnCancel: bool = True, openDelay: int = 0):
        super().__init__(parent)
        self._ui = Ui_ProgressDialog()
        self._ui.setupUi(self)

        self._autoCloseOnCancel = autoCloseOnCancel
        self._openDelay = openDelay

        self._canceled = False
        self._isOpen = False

        self._timer: QTimer = None

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

    def abort(self, text: str):
        if not self._isOpen:
            super().open()

        self.finish(text)

    def finish(self, text: str):
        self._clearTimer()

        self._ui.label.setText(text)
        self._ui.button.setText(self.tr('Close'))
        self._ui.progressBar.hide()
        self._ui.button.setEnabled(True)
        self._ui.button.show()

        self._ui.button.clicked.connect(self.close)

    def open(self):
        if self._openDelay > 0:
            if self._timer is None:
                self._timer = QTimer()
                self._timer.setInterval(self._openDelay)
                self._timer.setSingleShot(True)
                self._timer.timeout.connect(self._timeout)
                self._timer.start()
        else:
            super().open()
            self._isOpen = True

    def _timeout(self):
        super().open()
        self._isOpen = True

    def close(self):
        self._clearTimer()
        super().close()
        self._isOpen = False

    def cancel(self):
        self.close()

    def _cancelClicked(self):
        self._ui.button.setEnabled(False)
        self.cancelClicked.emit()
        self._canceled = True
        if self._autoCloseOnCancel:
            self.close()

    def _clearTimer(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer = None