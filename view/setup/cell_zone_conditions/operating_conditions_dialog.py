#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from coredb import coredb
from .operating_conditions_dialog_ui import Ui_OperatingConditionsDialog
from .cell_zone_db import CellZoneDB


class OperatingConditionsDialog(QDialog):
    def __init__(self, rname, czid):
        super().__init__()
        self._ui = Ui_OperatingConditionsDialog()
        self._ui.setupUi(self)

        self._rname = rname
        self._czid = czid

        self._db = coredb.CoreDB()
        self._xpath = CellZoneDB.getXPath(self._rname, self._czid)

        self._load()

    def _load(self):
        pass
