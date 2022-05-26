#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .porous_jump_dialog_ui import Ui_PorousJumpDialog


class PorousJumpDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_PorousJumpDialog()
        self._ui.setupUi(self)
