#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, Flag, auto

from PySide6.QtWidgets import QWidget, QMessageBox, QFormLayout

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from coredb.general_db import GeneralDB
from coredb.run_calculation_db import TimeSteppingMethod, DataWriteFormat, MachineType, RunCalculationDB
from .process_information_page_ui import Ui_ProcessInformationPage

class ProcessInformationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_ProcessInformationPage()
        self._ui.setupUi(self)
