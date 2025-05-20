#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWizardPage, QLineEdit

from widgets.enum_button_group import EnumButtonGroup

from baramFlow.coredb.models_db import MultiphaseModel
from .multiphase_model_page_ui import Ui_MultiphaseModelPage


class MultiphaseModelPage(QWizardPage):
    def __init__(self, *args, **kwargs):
        super(MultiphaseModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_MultiphaseModelPage()
        self._ui.setupUi(self)

        self._model = QLineEdit()

        self._modelRadios = EnumButtonGroup()
        self._modelRadios.addEnumButton(self._ui.off, MultiphaseModel.OFF)
        self._modelRadios.addEnumButton(self._ui.volumeOfFluid, MultiphaseModel.VOLUME_OF_FLUID)
        self._modelRadios.dataChecked.connect(self._modelChanged)
        self._modelRadios.setCheckedData(MultiphaseModel.OFF)

        self._ui.off.setChecked(True)

        self._ui.mixture.hide()
        self.registerField('multiphaseModel', self._model)

    def _modelChanged(self, model):
        self._model.setText(model.value)
