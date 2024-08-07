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

        self._ui.model.addEnumItems({
            PorousZoneModel.DARCY_FORCHHEIMER: self.tr('Darcy Forchheimer'),
            PorousZoneModel.POWER_LAW: self.tr('Power Law'),
        })

        self._connectSignalsSlots()

    def load(self):
        self._ui.model.setCurrentData(PorousZoneModel(self._db.getValue(self._xpath + '/model')))
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

    def updateDB(self, db):
        model = self._ui.model.currentData()
        db.setValue(self._xpath + '/model', model.value, None)

        if model == PorousZoneModel.DARCY_FORCHHEIMER:
            db.setValue(self._xpath + '/darcyForchheimer/direction1Vector/x', self._ui.direction1VectorX.text(),
                        self.tr('Direction-1 Vector X'))
            db.setValue(self._xpath + '/darcyForchheimer/direction1Vector/y', self._ui.direction1VectorY.text(),
                        self.tr('Direction-1 Vector Y'))
            db.setValue(self._xpath + '/darcyForchheimer/direction1Vector/z',
                          self._ui.direction1VectorZ.text(), self.tr('Direction-1 Vector Z'))
            db.setValue(self._xpath + '/darcyForchheimer/direction2Vector/x',
                          self._ui.direction2VectorX.text(), self.tr('Direction-2 Vector X'))
            db.setValue(self._xpath + '/darcyForchheimer/direction2Vector/y',
                          self._ui.direction2VectorY.text(), self.tr('Direction-2 Vector Y'))
            db.setValue(self._xpath + '/darcyForchheimer/direction2Vector/z',
                          self._ui.direction2VectorZ.text(), self.tr('Direction-2 Vector Z'))
            db.setValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/x',
                          self._ui.viscousResistanceCoefficientX.text(), self.tr('Inertial Resistance Coefficient X'))
            db.setValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/y',
                          self._ui.viscousResistanceCoefficientY.text(), self.tr('Inertial Resistance Coefficient Y'))
            db.setValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/z',
                          self._ui.viscousResistanceCoefficientZ.text(), self.tr('Inertial Resistance Coefficient Z'))
            db.setValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/x',
                          self._ui.inertialResistanceCoefficientX.text(), self.tr('Viscous Resistance Coefficient X'))
            db.setValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/y',
                          self._ui.inertialResistanceCoefficientY.text(), self.tr('Viscous Resistance Coefficient Y'))
            db.setValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/z',
                          self._ui.inertialResistanceCoefficientZ.text(), self.tr('Viscous Resistance Coefficient Z'))
        elif model == PorousZoneModel.POWER_LAW:
            db.setValue(self._xpath + '/powerLaw/c0', self._ui.c0.text(), self.tr('C0'))
            db.setValue(self._xpath + '/powerLaw/c1', self._ui.c1.text(), self.tr('C1'))

        return True

    def _connectSignalsSlots(self):
        self._ui.model.currentDataChanged.connect(self._modelChanged)

    def _modelChanged(self, model):
        self._ui.darcyForchheimer.setVisible(model == PorousZoneModel.DARCY_FORCHHEIMER)
        self._ui.powerLaw.setVisible(model == PorousZoneModel.POWER_LAW)
