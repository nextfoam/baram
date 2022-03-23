#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage

from .solver_type_page_ui import Ui_SolverTypePage


class SolverTypePage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(SolverTypePage, self).__init__(*args, **kwargs)

        self._ui = Ui_SolverTypePage()
        self._ui.setupUi(self)

        self._ui.PressureBased.setChecked(True)

