#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from view.step_page import StepPage
from .castellation_page_ui import Ui_CastellationPage
from .region_tab import RegionTab


class Tab(Enum):
    REGION = 0
    CASTELLATION = auto()


class CastellationPage(StepPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_CastellationPage()
        self._ui.setupUi(self)

        self._regionTab = RegionTab(self, self._ui)

        self._currentTab = self._ui.tabWidget.currentWidget()

        self._connectSignalsSlots()

    @classmethod
    def nextStepAvailable(cls):
        return False

    def closeEvent(self, ev):
        self._regionTab.close()

        super().close()

    def _connectSignalsSlots(self):
        self._ui.tabWidget.currentChanged.connect(self._currentTabChanged)

    def _currentTabChanged(self, index):
        if index == Tab.REGION.value:
            self._regionTab.activated()
        else:
            self._regionTab.deactivated()
