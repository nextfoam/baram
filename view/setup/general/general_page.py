#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from PySide6.QtWidgets import QWidget

from coredb import coredb
from coredb.general_db import GeneralDB
from .general_page_ui import Ui_GeneralPage


logger = logging.getLogger(__name__)


class GeneralPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_GeneralPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._load()

    def hideEvent(self, ev):
        if ev.spontaneous():
            return super().hideEvent(ev)

        xpath = GeneralDB.GENERAL_XPATH + '/timeTransient'

        if self._ui.transient_.isChecked():
            self._db.setValue(xpath, 'true')
        else:
            self._db.setValue(xpath, 'false')

        return super().hideEvent(ev)

    def _load(self):
        xpath = GeneralDB.GENERAL_XPATH + '/timeTransient'

        timeTransient = self._db.getValue(xpath)
        if timeTransient == 'true':
            self._ui.transient_.setChecked(True)
        else:
            self._ui.steady.setChecked(True)

