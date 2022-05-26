#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog

from coredb import coredb
from .supersonic_inflow_dialog_ui import Ui_SupersonicInflowDialog
from .turbulence_model import TurbulenceModel


class SupersonicInflowDialog(QDialog):
    BOUNDARY_CONDITIONS_XPATH = './/boundaryConditions'

    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_SupersonicInflowDialog()
        self._ui.setupUi(self)

        self._xpath = f'{self.BOUNDARY_CONDITIONS_XPATH}/boundaryCondition[@bcid="{bcid}"]'
        self._boundaryCondition = None

        self._db = coredb.CoreDB()

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)

        self._load()

    def _load(self):
        path = self._xpath + '/supersonicInflow'
        self._ui.xVelocity.setText(self._db.getValue(path + '/velocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(path + '/velocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(path + '/velocity/z'))
        self._ui.staticPressure.setText(self._db.getValue(path + '/staticPressure'))
        self._ui.staticTemperature.setText(self._db.getValue(path + '/staticTemperature'))

        self._turbulenceWidget.load(self._db, self._xpath)
