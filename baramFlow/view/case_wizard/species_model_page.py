#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage

from .species_model_page_ui import Ui_SpeciesModelPage


class SpeciesModelPage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(SpeciesModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_SpeciesModelPage()
        self._ui.setupUi(self)

        self._ui.notInclude.setChecked(True)
        self.registerField('speciesModelsInclude', self._ui.include)
