#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from .cyclic_dialog_ui import Ui_CyclicDialog
from .boundary_radio_group import BoundaryRadioGroup


class CyclicDialog(QDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_CyclicDialog()
        self._ui.setupUi(self)

        self._boundaryRadios = BoundaryRadioGroup()
        self._boundaryRadios.setup(self._ui.boundaryList, "cyclicAMI")
