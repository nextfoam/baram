#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QDialog

from .start_window_ui import Ui_StartWindow


class StartAction(Enum):
    ACTION_NEW = 0
    ACTION_OPEN = auto()


class StartWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_StartWindow()
        self._ui.setupUi(self)

        self._action = None

        self._connectSignalsSlots()

    def action(self):
        return self._action

    def _connectSignalsSlots(self):
        self._ui.newCase.clicked.connect(self._new)
        self._ui.open.clicked.connect(self._open)

    def _new(self):
        self._action = StartAction.ACTION_NEW
        self.done(QDialog.Accepted)

    def _open(self):
        self._action = StartAction.ACTION_OPEN
        self.done(QDialog.Accepted)