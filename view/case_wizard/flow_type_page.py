#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage

from .flow_type_page_ui import Ui_FlowTypePage


class FlowTypePage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(FlowTypePage, self).__init__(*args, **kwargs)

        self._ui = Ui_FlowTypePage()
        self._ui.setupUi(self)

        # self.setTitle(self.tr("Flow Type"))
        # self.setSubTitle(self.tr("Select flow type"))

        self._ui.incompressible.setChecked(True)
        self.registerField('flowType', self._ui.compressible)
