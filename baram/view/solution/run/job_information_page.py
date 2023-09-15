#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, Flag, auto

from PySide6.QtWidgets import QWidget, QMessageBox, QFormLayout

from baram.coredb import coredb
from baram.coredb.coredb_writer import CoreDBWriter
from baram.coredb.general_db import GeneralDB
from baram.coredb.run_calculation_db import TimeSteppingMethod, DataWriteFormat, RunCalculationDB
from .job_information_page_ui import Ui_JobInformationPage

class JobInformationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_JobInformationPage()
        self._ui.setupUi(self)