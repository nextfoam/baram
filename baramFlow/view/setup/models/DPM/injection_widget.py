#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QWidget

from baramFlow.base.model.model import DPM_INJECTION_TYPE_TEXTS
from .injection_widget_ui import Ui_InjectionWidget


class InjectionWidget(QWidget):
    def __init__(self, injection):
        super().__init__()
        self._ui = Ui_InjectionWidget()
        self._ui.setupUi(self)

        self._injection = None

        self.setInjection(injection)

    def injection(self):
        return self._injection

    def setInjection(self, injection):
        self._injection = injection

        self._ui.name.setText(injection.name)
        self._ui.type.setText(DPM_INJECTION_TYPE_TEXTS[injection.injector.type])
