#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import PorousZoneModel
from .porous_zone_widget_ui import Ui_porousZoneWidget


class PorousZoneWidget(QWidget):
    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_porousZoneWidget()
        self._ui.setupUi(self)
        self.setVisible(False)

        self._db = coredb.CoreDB()
        self._xpath = xpath + '/porous'

        self._connectSignalsSlots()

    def load(self):
        model = self._db.getValue(self._xpath + '/model')
        self._setupModelCombo(model)

        self._ui.direction1VectorX.setText(self._db.getValue(self._xpath + '/darcyForchheimer/direction1Vector/x'))
        self._ui.direction1VectorY.setText(self._db.getValue(self._xpath + '/darcyForchheimer/direction1Vector/y'))
        self._ui.direction1VectorZ.setText(self._db.getValue(self._xpath + '/darcyForchheimer/direction1Vector/z'))
        self._ui.direction2VectorX.setText(self._db.getValue(self._xpath + '/darcyForchheimer/direction2Vector/x'))
        self._ui.direction2VectorY.setText(self._db.getValue(self._xpath + '/darcyForchheimer/direction2Vector/y'))
        self._ui.direction2VectorZ.setText(self._db.getValue(self._xpath + '/darcyForchheimer/direction2Vector/z'))
        self._ui.viscousResistanceCoefficientX.setText(
            self._db.getValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/x'))
        self._ui.viscousResistanceCoefficientY.setText(
            self._db.getValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/y'))
        self._ui.viscousResistanceCoefficientZ.setText(
            self._db.getValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/z'))
        self._ui.inertialResistanceCoefficientX.setText(
            self._db.getValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/x'))
        self._ui.inertialResistanceCoefficientY.setText(
            self._db.getValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/y'))
        self._ui.inertialResistanceCoefficientZ.setText(
            self._db.getValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/z'))

        self._ui.c0.setText(self._db.getValue(self._xpath + '/powerLaw/c0'))
        self._ui.c1.setText(self._db.getValue(self._xpath + '/powerLaw/c1'))

    def appendToWriter(self, writer):
        model = self._ui.model.currentData()
        writer.append(self._xpath + '/model', model, None)

        if model == PorousZoneModel.DARCY_FORCHHEIMER.value:
            writer.append(self._xpath + '/darcyForchheimer/direction1Vector/x',
                          self._ui.direction1VectorX.text(), self.tr("Direction-1 Vector X"))
            writer.append(self._xpath + '/darcyForchheimer/direction1Vector/y',
                          self._ui.direction1VectorY.text(), self.tr("Direction-1 Vector Y"))
            writer.append(self._xpath + '/darcyForchheimer/direction1Vector/z',
                          self._ui.direction1VectorZ.text(), self.tr("Direction-1 Vector Z"))
            writer.append(self._xpath + '/darcyForchheimer/direction2Vector/x',
                          self._ui.direction2VectorX.text(), self.tr("Direction-2 Vector X"))
            writer.append(self._xpath + '/darcyForchheimer/direction2Vector/y',
                          self._ui.direction2VectorY.text(), self.tr("Direction-2 Vector Y"))
            writer.append(self._xpath + '/darcyForchheimer/direction2Vector/z',
                          self._ui.direction2VectorZ.text(), self.tr("Direction-2 Vector Z"))
            writer.append(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/x',
                          self._ui.viscousResistanceCoefficientX.text(), self.tr("Inertial Resistance Coefficient X"))
            writer.append(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/y',
                          self._ui.viscousResistanceCoefficientY.text(), self.tr("Inertial Resistance Coefficient Y"))
            writer.append(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/z',
                          self._ui.viscousResistanceCoefficientZ.text(), self.tr("Inertial Resistance Coefficient Z"))
            writer.append(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/x',
                          self._ui.inertialResistanceCoefficientX.text(), self.tr("Viscous Resistance Coefficient X"))
            writer.append(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/y',
                          self._ui.inertialResistanceCoefficientY.text(), self.tr("Viscous Resistance Coefficient Y"))
            writer.append(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/z',
                          self._ui.inertialResistanceCoefficientZ.text(), self.tr("Viscous Resistance Coefficient Z"))
        elif model == PorousZoneModel.POWER_LAW.value:
            writer.append(self._xpath + '/powerLaw/c0', self._ui.c0.text(), self.tr("C0"))
            writer.append(self._xpath + '/powerLaw/c1', self._ui.c1.text(), self.tr("C1"))

        return True

    def _setupModelCombo(self, current):
        self._addModelComboItem(current, PorousZoneModel.DARCY_FORCHHEIMER, self.tr("Darcy Forchheimer"))
        self._addModelComboItem(current, PorousZoneModel.POWER_LAW, self.tr("Power Law"))

    def _addModelComboItem(self, current, model, text):
        self._ui.model.addItem(text, model.value)
        if current == model.value:
            self._ui.model.setCurrentIndex(self._ui.model.count() - 1)

    def _connectSignalsSlots(self):
        self._ui.model.currentIndexChanged.connect(self._modelChanged)

    def _modelChanged(self):
        model = self._ui.model.currentData()
        self._ui.darcyForchheimer.setVisible(model == PorousZoneModel.DARCY_FORCHHEIMER.value)
        self._ui.powerLaw.setVisible(model == PorousZoneModel.POWER_LAW.value)
