#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from .reference_values_page_ui import Ui_ReferenceValuesPage


class ReferenceValuesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ReferenceValuesPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._load()

    def hideEvent(self, ev):
        if not ev.spontaneous():
            self.save()

        return super().hideEvent(ev)

    def save(self):
        pass

    def _load(self):
        pass
