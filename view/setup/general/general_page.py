#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from PySide6.QtWidgets import QWidget

from coredb import coredb
from .general_page_ui import Ui_GeneralPage


logger = logging.getLogger(__name__)


class GeneralPage(QWidget):
    MODEL_XPATH = './/general/timeTransient'

    def __init__(self):
        super().__init__()
        self._ui = Ui_GeneralPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._load()

    def hideEvent(self, ev):
        if ev.spontaneous():
            return

        if self._ui.transient_.isChecked():
            self._db.setValue(self.MODEL_XPATH, 'true')
        else:
            self._db.setValue(self.MODEL_XPATH, 'false')

    def _load(self):
        timeTransient = self._db.getValue(self.MODEL_XPATH)
        if timeTransient == 'true':
            self._ui.transient_.setChecked(True)
        else:
            self._ui.steady.setChecked(True)

