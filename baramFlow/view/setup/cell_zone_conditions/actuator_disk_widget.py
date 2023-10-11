#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from .actuator_disk_widget_ui import Ui_ActuatorDiskWidget


class ForceComputation(Enum):
    FROUDE = 'Froude'
    VARIABLE_SCALING = 'variableScaling'


class ActuatorDiskWidget(QWidget):
    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_ActuatorDiskWidget()
        self._ui.setupUi(self)
        self.setVisible(False)

        self._forceComputations = {
            self._ui.forceComputationRadioGroup.id(self._ui.froude): ForceComputation.FROUDE.value,
            self._ui.forceComputationRadioGroup.id(self._ui.variableScaling): ForceComputation.VARIABLE_SCALING.value,
        }

        self._db = coredb.CoreDB()
        self._xpath = xpath + '/actuatorDisk'

    def load(self):
        self._ui.diskDirectionX.setText(self._db.getValue(self._xpath + '/diskDirection/x'))
        self._ui.diskDirectionY.setText(self._db.getValue(self._xpath + '/diskDirection/y'))
        self._ui.diskDirectionZ.setText(self._db.getValue(self._xpath + '/diskDirection/z'))
        self._ui.powerCoefficient.setText(self._db.getValue(self._xpath + '/powerCoefficient'))
        self._ui.thrustCoefficient.setText(self._db.getValue(self._xpath + '/thrustCoefficient'))
        self._ui.diskArea.setText(self._db.getValue(self._xpath + '/diskArea'))
        self._ui.upstreamPointX.setText(self._db.getValue(self._xpath + '/upstreamPoint/x'))
        self._ui.upstreamPointY.setText(self._db.getValue(self._xpath + '/upstreamPoint/y'))
        self._ui.upstreamPointZ.setText(self._db.getValue(self._xpath + '/upstreamPoint/z'))
        self._getForceComputationRadio(self._db.getValue(self._xpath + '/forceComputation')).setChecked(True)

    def appendToWriter(self, writer):
        writer.append(self._xpath + '/diskDirection/x', self._ui.diskDirectionX.text(), self.tr("Disk Direction X"))
        writer.append(self._xpath + '/diskDirection/y', self._ui.diskDirectionY.text(), self.tr("Disk Direction Y"))
        writer.append(self._xpath + '/diskDirection/z', self._ui.diskDirectionZ.text(), self.tr("Disk Direction Z"))
        writer.append(self._xpath + '/powerCoefficient',
                      self._ui.powerCoefficient.text(), self.tr("Power Coefficient"))
        writer.append(self._xpath + '/thrustCoefficient',
                      self._ui.thrustCoefficient.text(), self.tr("Thrust Coefficient"))
        writer.append(self._xpath + '/diskArea', self._ui.diskArea.text(), self.tr("Disk Area"))
        writer.append(self._xpath + '/upstreamPoint/x', self._ui.upstreamPointX.text(), self.tr("Upstream Point X"))
        writer.append(self._xpath + '/upstreamPoint/y', self._ui.upstreamPointY.text(), self.tr("Upstream Point Y"))
        writer.append(self._xpath + '/upstreamPoint/z', self._ui.upstreamPointZ.text(), self.tr("Upstream Point Z"))
        writer.append(self._xpath + '/forceComputation', self._getForceComputationRadioValue(), None)

        return True

    def _getForceComputationRadio(self, value):
        return self._ui.forceComputationRadioGroup.button(
            list(self._forceComputations.keys())[list(self._forceComputations.values()).index(value)])

    def _getForceComputationRadioValue(self):
        return self._forceComputations[
            self._ui.forceComputationRadioGroup.id(self._ui.forceComputationRadioGroup.checkedButton())]
