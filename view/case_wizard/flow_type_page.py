#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage

from .flow_type_page_ui import Ui_FlowTypePage


class FlowTypePage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(FlowTypePage, self).__init__(*args, **kwargs)

        self._ui = Ui_FlowTypePage()
        self._ui.setupUi(self)

        self._ui.IncompressibleFlow.setChecked(True)
        self.registerField('compressibleFlow', self._ui.CompressibleFlow)





