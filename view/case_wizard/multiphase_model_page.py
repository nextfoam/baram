#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QWizardPage

from .multiphase_model_page_ui import Ui_MultiphaseModelPage


class MultiphaseModelPage(QWizardPage):
    class Model(Enum):
        OFF = auto()
        VOLUME_OF_FLUID = auto()

    def __init__(self, *args, **kwargs):
        super(MultiphaseModelPage, self).__init__(*args, **kwargs)

        self._ui = Ui_MultiphaseModelPage()
        self._ui.setupUi(self)

        self._ui.off.setChecked(True)
        self._ui.mixture.hide()

        self.registerField('multiphaseOff', self._ui.off)
        self.registerField('multiphaseVolumeOfFluid', self._ui.volumeOfFluid)
