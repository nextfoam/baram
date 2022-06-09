#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.widgets.resizable_dialog import ResizableDialog
from .supersonic_inflow_dialog_ui import Ui_SupersonicInflowDialog
from .turbulence_model import TurbulenceModel


class SupersonicInflowDialog(ResizableDialog):
    def __init__(self, bcid):
        super().__init__()
        self._ui = Ui_SupersonicInflowDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._boundaryCondition = None

        self._dao = SupersonicInflowDAO()

        self._turbulenceWidget = TurbulenceModel().boundaryConditionWidget(self)
        layout = self._ui.dialogContents.layout()
        layout.addWidget(self._turbulenceWidget)

        self._load()

    def _load(self):
        self._boundaryCondition = self._dao.getBoundaryCondition(self._bcid)
        self._ui.xVelocity.setText(self._boundaryCondition.velocity[0])
        self._ui.yVelocity.setText(self._boundaryCondition.velocity[1])
        self._ui.zVelocity.setText(self._boundaryCondition.velocity[2])
        self._ui.staticPressure.setText(self._boundaryCondition.staticPressure)
        self._ui.staticTemperature.setText(self._boundaryCondition.staticTemperature)


class SupersonicInflowDAO:
    BOUNDARY_CONDITION_XPATH = './/boundaryConditions/boundaryCondition'

    _db = coredb.CoreDB()

    def getBoundaryCondition(self, bcid):
        xpath = f'{self.BOUNDARY_CONDITION_XPATH}[@bcid="{bcid}"]/supersonicInflow'

        data = SupersonicInflowBoundaryCondition()
        data.velocity = self._getVector(xpath + "/velocity")
        data.staticPressure = self._db.getValue(xpath + "/staticPressure")
        data.staticTemperature = self._db.getValue(xpath + "/staticTemperature")

        return data

    def _getVector(self, xpath):
        return (self._db.getValue(xpath + "/x"),
                self._db.getValue(xpath + "/y"),
                self._db.getValue(xpath + "/z"))


class SupersonicInflowBoundaryCondition:
    def __init__(self):
        self._velocity = None
        self._staticPressure = None
        self._staticTemperature = None

    @property
    def velocity(self):
        return self._velocity

    @velocity.setter
    def velocity(self, velocity):
        self._velocity = velocity

    @property
    def staticPressure(self):
        return self._staticPressure

    @staticPressure.setter
    def staticPressure(self, staticPressure):
        self._staticPressure = staticPressure

    @property
    def staticTemperature(self):
        return self._staticTemperature

    @staticTemperature.setter
    def staticTemperature(self, staticTemperature):
        self._staticTemperature = staticTemperature



