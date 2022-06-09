#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb
from .actuator_disk_widget_ui import Ui_ActuatorDiskWidget


class ActuatorDiskWidget(QWidget):
    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_ActuatorDiskWidget()
        self._ui.setupUi(self)
        self.setVisible(False)

        self._db = coredb.CoreDB()
        self._xpath = xpath + '/actuatorDisk'

    def load(self):
        self._ui.diskDirectionX.setText(self._db.getValue(self._xpath + '/diskDirection/x'))
        self._ui.diskDirectionY.setText(self._db.getValue(self._xpath + '/diskDirection/y'))
        self._ui.diskDirectionZ.setText(self._db.getValue(self._xpath + '/diskDirection/z'))
        self._ui.powerCoefficient.setText(self._db.getValue(self._xpath + '/powerCoefficient'))
        self._ui.thrustCoefficient.setText(self._db.getValue(self._xpath + '/thrustCoefficient'))
        self._ui.diskArea.setText(self._db.getValue(self._xpath + '/diskArea'))
        self._ui.upstraemPointX.setText(self._db.getValue(self._xpath + '/upstreamPoint/x'))
        self._ui.upstraemPointY.setText(self._db.getValue(self._xpath + '/upstreamPoint/y'))
        self._ui.upstraemPointZ.setText(self._db.getValue(self._xpath + '/upstreamPoint/z'))

    def appendToWriter(self, writer):
        writer.append(self._xpath + '/diskDirection/x', self._ui.diskDirectionX.text(), self.tr("Disk Direction X"))
        writer.append(self._xpath + '/diskDirection/y', self._ui.diskDirectionY.text(), self.tr("Disk Direction Y"))
        writer.append(self._xpath + '/diskDirection/z', self._ui.diskDirectionZ.text(), self.tr("Disk Direction Z"))
        writer.append(self._xpath + '/powerCoefficient',
                      self._ui.powerCoefficient.text(), self.tr("Power Coefficient"))
        writer.append(self._xpath + '/thrustCoefficient',
                      self._ui.thrustCoefficient.text(), self.tr("Thrust Coefficient"))
        writer.append(self._xpath + '/diskArea', self._ui.diskArea.text(), self.tr("Disk Area"))
        writer.append(self._xpath + '/upstreamPoint/x', self._ui.upstraemPointX.text(), self.tr("Upstream Point X"))
        writer.append(self._xpath + '/upstreamPoint/y', self._ui.upstraemPointY.text(), self.tr("Upstream Point Y"))
        writer.append(self._xpath + '/upstreamPoint/z', self._ui.upstraemPointZ.text(), self.tr("Upstream Point Z"))
