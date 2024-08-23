#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox, QWidget, QGridLayout, QLabel, QLineEdit, QFormLayout

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.boundary_db import BoundaryDB, WallVelocityCondition, WallTemperature, ContactAngleModel, ContactAngleLimit
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from baramFlow.view.widgets.enum_combo_box import EnumComboBox
from .wall_dialog_ui import Ui_WallDialog


class ContactAnglesWidget(QWidget):
    def __init__(self, parent, labels):
        super().__init__()
        self._rows = []

        self._layout = QGridLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        parent.layout().addWidget(self)

        column = 2
        for label in labels:
            self._layout.addWidget(QLabel(label), 0, column)
            # self._layout.setColumnStretch(column, 1)
            column += 1

    def addRow(self, mid1, mid2, name1, name2, values):
        row = self._layout.count()

        self._layout.addWidget(QLabel(name1), row, 0)
        self._layout.addWidget(QLabel(name2), row, 1)

        editors = []
        column = 2
        for v in values:
            e = QLineEdit(v)
            editors.append(e)
            self._layout.addWidget(e, row, column)
            column += 1

        self._rows.append((mid1, mid2, name1, name2, editors))

    def count(self):
        return len(self._rows)

    def row(self, index):
        mid1, mid2, name1, name2, editors = self._rows[index]
        return mid1, mid2, name1, name2, [e.text() for e in editors]


class WallDialog(ResizableDialog):
    RELATIVE_XPATH = '/wall'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_WallDialog()
        self._ui.setupUi(self)

        self._bcid = bcid

        self._constantContactAngles = None
        self._dynamicContactAngles = None

        self._velocityConditionCombo = None
        self._temperatureTypeCombo = None
        self._contactAngleModelCombo = None
        self._contactAngleLimitCombo = None

        self._xpath = BoundaryDB.getXPath(bcid)

        self._setupVelocityConditionCombo()

        self._load()

    def accept(self):
        xpath = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()
        type_ = self._velocityConditionCombo.currentValue()
        writer.append(xpath + '/velocity/type', self._velocityConditionCombo.currentValue(), None)
        if type_ == WallVelocityCondition.TRANSLATIONAL_MOVING_WALL.value:
            writer.append(xpath + '/velocity/translationalMovingWall/velocity/x',
                          self._ui.xVelocity.text(), self.tr('X-Velocity'))
            writer.append(xpath + '/velocity/translationalMovingWall/velocity/y',
                          self._ui.yVelocity.text(), self.tr('Y-Velocity'))
            writer.append(xpath + '/velocity/translationalMovingWall/velocity/z',
                          self._ui.zVelocity.text(), self.tr('Z-Velocity'))
        elif type_ == WallVelocityCondition.ROTATIONAL_MOVING_WALL.value:
            writer.append(xpath + '/velocity/rotationalMovingWall/speed', self._ui.speed.text(), self.tr('Speed'))
            writer.append(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/x',
                          self._ui.rotationAxisX.text(), self.tr('Rotation-Axis Origin X'))
            writer.append(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/y',
                          self._ui.rotationAxisY.text(), self.tr('Rotation-Axis Origin Y'))
            writer.append(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/z',
                          self._ui.rotationAxisZ.text(), self.tr('Rotation-Axis Origin Z'))
            writer.append(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/x',
                          self._ui.rotationDirectionX.text(), self.tr('Rotation-Axis Direction X'))
            writer.append(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/y',
                          self._ui.rotationDirectionY.text(), self.tr('Rotation-Axis Direction Y'))
            writer.append(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/z',
                          self._ui.rotationDirectionZ.text(), self.tr('Rotation-Axis Direction Z'))

        if ModelsDB.isEnergyModelOn():
            writer.append(xpath + '/temperature/type', self._temperatureTypeCombo.currentValue(), None)
            if self._temperatureTypeCombo.isSelected(WallTemperature.CONSTANT_TEMPERATURE):
                writer.append(xpath + '/temperature/temperature', self._ui.temperature.text(), self.tr('Temperature'))
            elif self._temperatureTypeCombo.isSelected(WallTemperature.CONSTANT_HEAT_FLUX):
                writer.append(xpath + '/temperature/heatFlux', self._ui.heatFlux.text(), self.tr('Heat Flux'))
            elif self._temperatureTypeCombo.isSelected(WallTemperature.CONVECTION):
                writer.append(xpath + '/temperature/heatTransferCoefficient', self._ui.heatTransferCoefficient.text(),
                              self.tr('Heat Transfer Coefficient'))
                writer.append(xpath + '/temperature/freeStreamTemperature', self._ui.freeStreamTemperature.text(),
                              self.tr('Free Stream Temperature'))

        if self._ui.contactAngleGroup.isVisible():
            writer.append(xpath + '/wallAdhesions/model', self._contactAngleModelCombo.currentValue(), None)
            if self._ui.contactAngleLimit:
                writer.append(xpath + '/wallAdhesions/limit', self._contactAngleLimitCombo.currentValue(), None)

            if self._contactAngleModelCombo.isSelected(ContactAngleModel.CONSTANT):
                for i in range(self._constantContactAngles.count()):
                    mid1, mid2, name1, name2, [ca] = self._constantContactAngles.row(i)
                    caxpath = f'{xpath}/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'
                    writer.append(caxpath + '/contactAngle', ca, self.tr(f'Constant Angle of ({name1}, {name2})'))
            elif self._contactAngleModelCombo.isSelected(ContactAngleModel.DYNAMIC):
                for i in range(self._constantContactAngles.count()):
                    mid1, mid2, name1, name2, [ca1, ca2, ca3, scale] = self._dynamicContactAngles.row(i)
                    caxpath = f'{xpath}/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'
                    writer.append(caxpath + '/contactAngle', ca1,
                                  self.tr(f'Equilibrium CA of ({name1}, {name2})'))
                    writer.append(caxpath + '/advancingContactAngle', ca2,
                                  self.tr(f'Advancing CA of ({name1}, {name2})'))
                    writer.append(caxpath + '/recedingContactAngle', ca3,
                                  self.tr(f'Receding CA of ({name1}, {name2})'))
                    writer.append(caxpath + '/characteristicVelocityScale', scale,
                                  self.tr(f'Characteristic Velocity Scale of ({name1}, {name2})'))

        if ModelsDB.isRadiationModelOn():
            writer.append(xpath + '/radiation/wallEmissivity', self._ui.wallEmissivity.text(),
                          self.tr('Wall Emissivity'))
            writer.append(xpath + '/radiation/radiativeFluxRelaxation', self._ui.radiativeFluxRelaxation.text(),
                          self.tr('Radiative Flux Relaxation'))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._velocityConditionCombo.setCurrentValue(db.getValue(xpath + '/velocity/type'))
        self._ui.xVelocity.setText(db.getValue(xpath + '/velocity/translationalMovingWall/velocity/x'))
        self._ui.yVelocity.setText(db.getValue(xpath + '/velocity/translationalMovingWall/velocity/y'))
        self._ui.zVelocity.setText(db.getValue(xpath + '/velocity/translationalMovingWall/velocity/z'))
        self._ui.speed.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/speed'))
        self._ui.rotationAxisX.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/x'))
        self._ui.rotationAxisY.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/y'))
        self._ui.rotationAxisZ.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/z'))
        self._ui.rotationDirectionX.setText(
            db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/x'))
        self._ui.rotationDirectionY.setText(
            db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/y'))
        self._ui.rotationDirectionZ.setText(
            db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/z'))

        if ModelsDB.isEnergyModelOn():
            self._setupTemperatureCombo()
            self._temperatureTypeCombo.setCurrentValue(db.getValue(xpath + '/temperature/type'))
            self._ui.temperature.setText(db.getValue(xpath + '/temperature/temperature'))
            self._ui.heatFlux.setText(db.getValue(xpath + '/temperature/heatFlux'))
            self._ui.heatTransferCoefficient.setText(db.getValue(xpath + '/temperature/heatTransferCoefficient'))
            self._ui.freeStreamTemperature.setText(db.getValue(xpath + '/temperature/freeStreamTemperature'))
            self._temperatureTypeChanged()
        else:
            self._ui.temperatureGroup.hide()

        rname = BoundaryDB.getBoundaryRegion(self._bcid)
        secondaryMaterials = RegionDB.getSecondaryMaterials(rname) if  ModelsDB.isMultiphaseModelOn() else None
        if secondaryMaterials:
            self._loadContactAngles(rname, secondaryMaterials)
            self._setupContactAngleModelCombo()
            self._contactAngleModelCombo.setCurrentValue(db.getValue(xpath + '/wallAdhesions/model'))

        if not secondaryMaterials:
            self._ui.contactAngleGroup.hide()
        elif len(secondaryMaterials) > 1:
            self._ui.contactAngleFormLayout.removeRow(self._ui.contactAngleLimit)
            self._ui.contactAngleLimit = None
        else:
            self._setupContactAngleLimitCombo()
            self._contactAngleLimitCombo.setCurrentValue(db.getValue(xpath + '/wallAdhesions/limit'))

        if ModelsDB.isRadiationModelOn():
            self._ui.wallEmissivity.setText(db.getValue(xpath + '/radiation/wallEmissivity'))
            self._ui.radiativeFluxRelaxation.setText(db.getValue(xpath + '/radiation/radiativeFluxRelaxation'))
        else:
            self._ui.radiation.hide()

    def _loadContactAngles(self, rname, secondaryMaterials):
        def addAdhesionRows(mid1, mid2):
            db = coredb.CoreDB()
            xpath = f'{self._xpath}{self.RELATIVE_XPATH}/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'
            self._constantContactAngles.addRow(mid1, mid2, materials[mid1], materials[mid2],
                                               [db.getValue(xpath + '/contactAngle')])
            self._dynamicContactAngles.addRow(mid1, mid2, materials[mid1], materials[mid2],
                                              [db.getValue(xpath + '/contactAngle'),
                                               db.getValue(xpath + '/advancingContactAngle'),
                                               db.getValue(xpath + '/recedingContactAngle'),
                                               db.getValue(xpath + '/characteristicVelocityScale')])

        self._constantContactAngles = ContactAnglesWidget(
            self._ui.contactAngleGroup, [self.tr('Constant Angle (degree)')])
        self._dynamicContactAngles = ContactAnglesWidget(self._ui.contactAngleGroup,
                                                         [self.tr('Equilibrium CA\n (deg)'),
                                                          self.tr('Advancing CA\n (deg)'),
                                                          self.tr('Receding CA\n (deg)'),
                                                          self.tr('Characteristic Velocity Scale\n (m/s)')])

        mid = RegionDB.getMaterial(rname)
        materials = {mid: MaterialDB.getName(mid)}

        count = len(secondaryMaterials)
        for i in range(count):
            materials[secondaryMaterials[i]] = MaterialDB.getName(secondaryMaterials[i])
            addAdhesionRows(mid, secondaryMaterials[i])

        for i in range(count):
            for j in range(i + 1, count):
                addAdhesionRows(secondaryMaterials[i], secondaryMaterials[j])

    def _setupVelocityConditionCombo(self):
        self._velocityConditionCombo = EnumComboBox(self._ui.velocityCondition)
        self._velocityConditionCombo.currentValueChanged.connect(self._velocityConditionChanged)

        self._velocityConditionCombo.addItem(WallVelocityCondition.NO_SLIP, self.tr('No Slip'))
        self._velocityConditionCombo.addItem(WallVelocityCondition.SLIP, self.tr('Slip'))
        self._velocityConditionCombo.addItem(WallVelocityCondition.MOVING_WALL, self.tr('Moving Wall'))
        if not GeneralDB.isCompressible() and not ModelsDB.isMultiphaseModelOn():
            self._velocityConditionCombo.addItem(WallVelocityCondition.ATMOSPHERIC_WALL, self.tr('Atmospheric Wall'))
        self._velocityConditionCombo.addItem(WallVelocityCondition.TRANSLATIONAL_MOVING_WALL,
                                             self.tr('Translational Moving Wall'))
        self._velocityConditionCombo.addItem(WallVelocityCondition.ROTATIONAL_MOVING_WALL,
                                             self.tr('Rotational Moving Wall'))

    def _setupTemperatureCombo(self):
        self._temperatureTypeCombo = EnumComboBox(self._ui.temperatureType)
        self._temperatureTypeCombo.currentValueChanged.connect(self._temperatureTypeChanged)

        self._temperatureTypeCombo.addItem(WallTemperature.ADIABATIC, self.tr('Adiabatic'))
        self._temperatureTypeCombo.addItem(WallTemperature.CONSTANT_TEMPERATURE, self.tr('Constant Temperature'))
        self._temperatureTypeCombo.addItem(WallTemperature.CONSTANT_HEAT_FLUX, self.tr('Constant Heat Flux'))
        self._temperatureTypeCombo.addItem(WallTemperature.CONVECTION, self.tr('Convection'))

    def _setupContactAngleModelCombo(self):
        self._contactAngleModelCombo = EnumComboBox(self._ui.contactAngleModel)
        self._contactAngleModelCombo.currentValueChanged.connect(self._contactAngleTypeChanged)

        self._contactAngleModelCombo.addItem(ContactAngleModel.DISABLE, self.tr('Disable'))
        self._contactAngleModelCombo.addItem(ContactAngleModel.CONSTANT, self.tr('Constant'))
        self._contactAngleModelCombo.addItem(ContactAngleModel.DYNAMIC, self.tr('Dynamic'))

    def _setupContactAngleLimitCombo(self):
        self._contactAngleLimitCombo = EnumComboBox(self._ui.contactAngleLimit)

        self._contactAngleLimitCombo.addItem(ContactAngleLimit.NONE, self.tr('None'))
        self._contactAngleLimitCombo.addItem(ContactAngleLimit.GRADIENT, self.tr('Gradient'))
        self._contactAngleLimitCombo.addItem(ContactAngleLimit.ZERO_GRADIENT, self.tr('Zero Gradient'))
        self._contactAngleLimitCombo.addItem(ContactAngleLimit.ALPHA, self.tr('Alpha'))

    def _velocityConditionChanged(self):
        self._ui.translationalMovingWall.setVisible(
            self._velocityConditionCombo.isSelected(WallVelocityCondition.TRANSLATIONAL_MOVING_WALL))
        self._ui.rotationalMovingWall.setVisible(
            self._velocityConditionCombo.isSelected(WallVelocityCondition.ROTATIONAL_MOVING_WALL))

    def _temperatureTypeChanged(self):
        self._ui.constantTemperature.setVisible(
            self._temperatureTypeCombo.isSelected(WallTemperature.CONSTANT_TEMPERATURE))
        self._ui.constantHeatFlux.setVisible(self._temperatureTypeCombo.isSelected(WallTemperature.CONSTANT_HEAT_FLUX))
        self._ui.convection.setVisible(self._temperatureTypeCombo.isSelected(WallTemperature.CONVECTION))

    def _contactAngleTypeChanged(self):
        if self._contactAngleLimitCombo:
            if self._contactAngleModelCombo.isSelected(ContactAngleModel.DISABLE):
                if self._ui.contactAngleFormLayout.rowCount() > 1:
                    self._ui.contactAngleFormLayout.removeItem(
                        self._ui.contactAngleFormLayout.itemAt(1, QFormLayout.LabelRole))
                    self._ui.contactAngleFormLayout.removeItem(
                        self._ui.contactAngleFormLayout.itemAt(1, QFormLayout.FieldRole))
                    self._ui.contactAngleFormLayout.removeRow(1)
                    self._ui.contactAngleLimitLabel.setParent(None)
                    self._ui.contactAngleLimit.setParent(None)
            elif self._ui.contactAngleFormLayout.rowCount() < 2:
                self._ui.contactAngleFormLayout.addRow(self._ui.contactAngleLimitLabel, self._ui.contactAngleLimit)
        self._constantContactAngles.setVisible(self._contactAngleModelCombo.isSelected(ContactAngleModel.CONSTANT))
        self._dynamicContactAngles.setVisible(self._contactAngleModelCombo.isSelected(ContactAngleModel.DYNAMIC))
