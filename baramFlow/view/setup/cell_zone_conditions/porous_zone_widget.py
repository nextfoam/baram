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

        self._xpath = xpath + '/porous'

        self._ui.model.addEnumItems({
            PorousZoneModel.DARCY_FORCHHEIMER: self.tr('Darcy Forchheimer'),
            PorousZoneModel.POWER_LAW: self.tr('Power Law'),
        })

        self._connectSignalsSlots()

    def load(self):
        db = coredb.CoreDB()
        self._ui.model.setCurrentData(PorousZoneModel(db.getValue(self._xpath + '/model')))
        self._ui.direction1VectorX.setText(db.getValue(self._xpath + '/darcyForchheimer/direction1Vector/x'))
        self._ui.direction1VectorY.setText(db.getValue(self._xpath + '/darcyForchheimer/direction1Vector/y'))
        self._ui.direction1VectorZ.setText(db.getValue(self._xpath + '/darcyForchheimer/direction1Vector/z'))
        self._ui.direction2VectorX.setText(db.getValue(self._xpath + '/darcyForchheimer/direction2Vector/x'))
        self._ui.direction2VectorY.setText(db.getValue(self._xpath + '/darcyForchheimer/direction2Vector/y'))
        self._ui.direction2VectorZ.setText(db.getValue(self._xpath + '/darcyForchheimer/direction2Vector/z'))
        self._ui.viscousResistanceCoefficientX.setText(
            db.getValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/x'))
        self._ui.viscousResistanceCoefficientY.setText(
            db.getValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/y'))
        self._ui.viscousResistanceCoefficientZ.setText(
            db.getValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/z'))
        self._ui.inertialResistanceCoefficientX.setText(
            db.getValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/x'))
        self._ui.inertialResistanceCoefficientY.setText(
            db.getValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/y'))
        self._ui.inertialResistanceCoefficientZ.setText(
            db.getValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/z'))

        self._ui.c0.setText(db.getValue(self._xpath + '/powerLaw/c0'))
        self._ui.c1.setText(db.getValue(self._xpath + '/powerLaw/c1'))

    def updateDB(self, newDB):
        model = self._ui.model.currentData()
        newDB.setValue(self._xpath + '/model', model.value, None)

        if model == PorousZoneModel.DARCY_FORCHHEIMER:
            newDB.setValue(self._xpath + '/darcyForchheimer/direction1Vector/x', self._ui.direction1VectorX.text(),
                        self.tr('Direction-1 Vector X'))
            newDB.setValue(self._xpath + '/darcyForchheimer/direction1Vector/y', self._ui.direction1VectorY.text(),
                        self.tr('Direction-1 Vector Y'))
            newDB.setValue(self._xpath + '/darcyForchheimer/direction1Vector/z',
                          self._ui.direction1VectorZ.text(), self.tr('Direction-1 Vector Z'))
            newDB.setValue(self._xpath + '/darcyForchheimer/direction2Vector/x',
                          self._ui.direction2VectorX.text(), self.tr('Direction-2 Vector X'))
            newDB.setValue(self._xpath + '/darcyForchheimer/direction2Vector/y',
                          self._ui.direction2VectorY.text(), self.tr('Direction-2 Vector Y'))
            newDB.setValue(self._xpath + '/darcyForchheimer/direction2Vector/z',
                          self._ui.direction2VectorZ.text(), self.tr('Direction-2 Vector Z'))
            newDB.setValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/x',
                          self._ui.viscousResistanceCoefficientX.text(), self.tr('Inertial Resistance Coefficient X'))
            newDB.setValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/y',
                          self._ui.viscousResistanceCoefficientY.text(), self.tr('Inertial Resistance Coefficient Y'))
            newDB.setValue(self._xpath + '/darcyForchheimer/viscousResistanceCoefficient/z',
                          self._ui.viscousResistanceCoefficientZ.text(), self.tr('Inertial Resistance Coefficient Z'))
            newDB.setValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/x',
                          self._ui.inertialResistanceCoefficientX.text(), self.tr('Viscous Resistance Coefficient X'))
            newDB.setValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/y',
                          self._ui.inertialResistanceCoefficientY.text(), self.tr('Viscous Resistance Coefficient Y'))
            newDB.setValue(self._xpath + '/darcyForchheimer/inertialResistanceCoefficient/z',
                          self._ui.inertialResistanceCoefficientZ.text(), self.tr('Viscous Resistance Coefficient Z'))
        elif model == PorousZoneModel.POWER_LAW:
            newDB.setValue(self._xpath + '/powerLaw/c0', self._ui.c0.text(), self.tr('C0'))
            newDB.setValue(self._xpath + '/powerLaw/c1', self._ui.c1.text(), self.tr('C1'))

        return True

    def _connectSignalsSlots(self):
        self._ui.model.currentDataChanged.connect(self._modelChanged)

    def _modelChanged(self, model):
        self._ui.darcyForchheimer.setVisible(model == PorousZoneModel.DARCY_FORCHHEIMER)
        self._ui.powerLaw.setVisible(model == PorousZoneModel.POWER_LAW)
