#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage

from .energy_model_page_ui import Ui_EnergyModelPage


class EnergyModelPage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(EnergyModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_EnergyModelPage()
        self._ui.setupUi(self)

        self._ui.NotIncude.setChecked(True)
        self.registerField('energyModelIncluded', self._ui.Include)

