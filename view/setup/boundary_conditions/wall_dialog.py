#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.resizable_dialog import ResizableDialog
from view.setup.models.models_db import ModelsDB
from .wall_dialog_ui import Ui_WallDialog
from .boundary_db import BoundaryDB, WallVelocityCondition, WallTemperature


class WallDialog(ResizableDialog):
    RELATIVE_PATH = '/wall'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_WallDialog()
        self._ui.setupUi(self)

        self._velocityConditions = {
            WallVelocityCondition.NO_SLIP.value: self.tr("No Slip"),
            WallVelocityCondition.SLIP.value: self.tr("Slip"),
            WallVelocityCondition.MOVING_WALL.value: self.tr("Moving Wall"),
            WallVelocityCondition.ATMOSPHERIC_WALL.value: self.tr("Atmospheric Wall"),
            WallVelocityCondition.TRANSLATIONAL_MOVING_WALL.value: self.tr("Translational Moving Wall"),
            WallVelocityCondition.ROTATIONAL_MOVING_WALL.value: self.tr("Rotational Moving Wall"),
        }
        self._temperatureTypes = {
            WallTemperature.ADIABATIC.value: self.tr("Adiabatic"),
            WallTemperature.CONSTANT_TEMPERATURE.value: self.tr("Constant Temperature"),
            WallTemperature.CONSTANT_HEAT_FLUX.value: self.tr("Constant Heat Flux"),
            WallTemperature.CONVECTION.value: self.tr("Convection"),
        }

        self._addVelocityConditionComboItem(WallVelocityCondition.NO_SLIP)
        self._addVelocityConditionComboItem(WallVelocityCondition.SLIP)
        self._addVelocityConditionComboItem(WallVelocityCondition.MOVING_WALL)
        if not ModelsDB.isEnergyModelOn():
            self._addVelocityConditionComboItem(WallVelocityCondition.ATMOSPHERIC_WALL)
        self._addVelocityConditionComboItem(WallVelocityCondition.TRANSLATIONAL_MOVING_WALL)
        self._addVelocityConditionComboItem(WallVelocityCondition.ROTATIONAL_MOVING_WALL)

        self._setupTemperatureCombo()

        if not ModelsDB.isRadiationModelOn():
            self._ui.radiation.hide()

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_PATH

        writer = CoreDBWriter()
        type_ = self._ui.velocityCondition.currentData()
        writer.append(path + '/velocity/type', type_, None)
        if type_ == WallVelocityCondition.TRANSLATIONAL_MOVING_WALL.value:
            writer.append(path + '/velocity/translationalMovingWall/velocity/x', self._ui.xVelocity.text(), self.tr("X-Velocity"))
            writer.append(path + '/velocity/translationalMovingWall/velocity/y', self._ui.yVelocity.text(), self.tr("Y-Velocity"))
            writer.append(path + '/velocity/translationalMovingWall/velocity/z', self._ui.zVelocity.text(), self.tr("Z-Velocity"))
        elif type_ == WallVelocityCondition.ROTATIONAL_MOVING_WALL.value:
            writer.append(path + '/velocity/rotationalMovingWall/speed', self._ui.speed.text(), self.tr("Speed"))
            writer.append(path + '/velocity/rotationalMovingWall/rotationAxisOrigin/x', self._ui.rotationAxisX.text(), self.tr("Rotation-Axis Origin X"))
            writer.append(path + '/velocity/rotationalMovingWall/rotationAxisOrigin/y', self._ui.rotationAxisY.text(), self.tr("Rotation-Axis Origin Y"))
            writer.append(path + '/velocity/rotationalMovingWall/rotationAxisOrigin/z', self._ui.rotationAxisZ.text(), self.tr("Rotation-Axis Origin Z"))
            writer.append(path + '/velocity/rotationalMovingWall/rotationAxisDirection/x', self._ui.rotationDirectionX.text(), self.tr("Rotation-Axis Direction X"))
            writer.append(path + '/velocity/rotationalMovingWall/rotationAxisDirection/y', self._ui.rotationDirectionY.text(), self.tr("Rotation-Axis Direction Y"))
            writer.append(path + '/velocity/rotationalMovingWall/rotationAxisDirection/z', self._ui.rotationDirectionZ.text(), self.tr("Rotation-Axis Direction Z"))

        type_ = self._ui.temperatureType.currentData()
        writer.append(path + '/temperature/type', type_, None)
        if type_ == WallTemperature.CONSTANT_TEMPERATURE.value:
            writer.append(path + '/temperature/temperature', self._ui.temperature.text(), self.tr("Temperature"))
        elif type_ == WallTemperature.CONSTANT_HEAT_FLUX.value:
            writer.append(path + '/temperature/heatFlux', self._ui.heatFlux.text(), self.tr("Heat Flux"))
        elif type_ == WallTemperature.CONVECTION.value:
            writer.append(path + '/temperature/heatTransferCoefficient', self._ui.heatTransferCoefficient.text(), self.tr("Heat Transfer Coefficient"))
            writer.append(path + '/temperature/freeStreamTemperature', self._ui.freeStreamTemperature.text(), self.tr("Free Stream Temperature"))

        if ModelsDB.isRadiationModelOn():
            writer.append(path + '/radiation/wallEmissivity', self._ui.wallEmissivity.text(), self.tr("Wall Emissivity"))
            writer.append(path + '/radiation/radiativeFluxRelaxation', self._ui.radiativeFluxRelaxation.text(), self.tr("Radiative Flux Relaxation"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _connectSignalsSlots(self):
        self._ui.velocityCondition.currentIndexChanged.connect(self._velocityConditionChanged)
        self._ui.temperatureType.currentIndexChanged.connect(self._temperatureTypeChanged)

    def _load(self):
        path = self._xpath + self.RELATIVE_PATH

        type_ = self._db.getValue(path + '/velocity/type')
        self._ui.velocityCondition.setCurrentText(self._velocityConditions[type_])
        self._ui.xVelocity.setText(self._db.getValue(path + '/velocity/translationalMovingWall/velocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(path + '/velocity/translationalMovingWall/velocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(path + '/velocity/translationalMovingWall/velocity/z'))
        self._ui.speed.setText(self._db.getValue(path + '/velocity/rotationalMovingWall/speed'))
        self._ui.rotationAxisX.setText(self._db.getValue(path + '/velocity/rotationalMovingWall/rotationAxisOrigin/x'))
        self._ui.rotationAxisY.setText(self._db.getValue(path + '/velocity/rotationalMovingWall/rotationAxisOrigin/y'))
        self._ui.rotationAxisZ.setText(self._db.getValue(path + '/velocity/rotationalMovingWall/rotationAxisOrigin/z'))
        self._ui.rotationDirectionX.setText(
            self._db.getValue(path + '/velocity/rotationalMovingWall/rotationAxisDirection/x'))
        self._ui.rotationDirectionY.setText(
            self._db.getValue(path + '/velocity/rotationalMovingWall/rotationAxisDirection/y'))
        self._ui.rotationDirectionZ.setText(
            self._db.getValue(path + '/velocity/rotationalMovingWall/rotationAxisDirection/z'))
        self._velocityConditionChanged()

        type_ = self._db.getValue(path + '/temperature/type')
        self._ui.temperatureType.setCurrentText(self._temperatureTypes[type_])
        self._ui.temperature.setText(self._db.getValue(path + '/temperature/temperature'))
        self._ui.heatFlux.setText(self._db.getValue(path + '/temperature/heatFlux'))
        self._ui.heatTransferCoefficient.setText(self._db.getValue(path + '/temperature/heatTransferCoefficient'))
        self._ui.freeStreamTemperature.setText(self._db.getValue(path + '/temperature/freeStreamTemperature'))
        self._temperatureTypeChanged()

        if ModelsDB.isRadiationModelOn():
            self._ui.wallEmissivity.setText(self._db.getValue(path + '/radiation/wallEmissivity'))
            self._ui.radiativeFluxRelaxation.setText(self._db.getValue(path + '/radiation/radiativeFluxRelaxation'))

    def _addVelocityConditionComboItem(self, item):
        self._ui.velocityCondition.addItem(self._velocityConditions[item.value], item.value)

    def _setupTemperatureCombo(self):
        for value, text in self._temperatureTypes.items():
            self._ui.temperatureType.addItem(text, value)

    def _velocityConditionChanged(self):
        condition = self._ui.velocityCondition.currentData()
        self._ui.translationalMovingWall.setVisible(
            condition == WallVelocityCondition.TRANSLATIONAL_MOVING_WALL.value)
        self._ui.rotationalMovingWall.setVisible(
            condition == WallVelocityCondition.ROTATIONAL_MOVING_WALL.value)

    def _temperatureTypeChanged(self):
        temperature = self._ui.temperatureType.currentData()
        self._ui.constantTemperature.setVisible(temperature == WallTemperature.CONSTANT_TEMPERATURE.value)
        self._ui.constantHeatFlux.setVisible(temperature == WallTemperature.CONSTANT_HEAT_FLUX.value)
        self._ui.convection.setVisible(temperature == WallTemperature.CONVECTION.value)
