#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage, QLineEdit

from baram.coredb.models_db import MultiphaseModel
from baram.view.widgets.enum_button_group import EnumButtonGroup
from .multiphase_model_page_ui import Ui_MultiphaseModelPage


class MultiphaseModelPage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(MultiphaseModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_MultiphaseModelPage()
        self._ui.setupUi(self)

        self._model = QLineEdit()

        self._modelRadios = EnumButtonGroup()
        self._modelRadios.addButton(self._ui.off, MultiphaseModel.OFF)
        self._modelRadios.addButton(self._ui.volumeOfFluid, MultiphaseModel.VOLUME_OF_FLUID)
        self._modelRadios.valueChecked.connect(self._modelChanged)
        self._modelRadios.setCheckedButton(MultiphaseModel.OFF)

        self._ui.off.setChecked(True)

        self._ui.mixture.hide()
        self.registerField('multiphaseModel', self._model)

    def _modelChanged(self, model):
        self._model.setText(model)
