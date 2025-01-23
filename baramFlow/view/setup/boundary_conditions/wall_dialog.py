#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.boundary_db import BoundaryDB, WallVelocityCondition, WallTemperature
from baramFlow.coredb.boundary_db import ContactAngleModel, ContactAngleLimit
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .wall_dialog_ui import Ui_WallDialog
from .wall_layers_widget import WallLayersWidget


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

        self._phases = 1

        self._constantContactAngles = None
        self._dynamicContactAngles = None

        self._wallLayersWidget = None

        self._xpath = BoundaryDB.getXPath(bcid)

        self._connectSignalsSlots()

        self._setupVelocityConditionCombo()

        self._load()
    
    @qasync.asyncSlot()
    async def accept(self):
        try:
            with coredb.CoreDB() as db:
                xpath = self._xpath + self.RELATIVE_XPATH

                velocityCondition = WallVelocityCondition(self._ui.velocityCondition.currentData())
                db.setValue(xpath + '/velocity/type', velocityCondition.value, None)
                if velocityCondition == WallVelocityCondition.TRANSLATIONAL_MOVING_WALL:
                    db.setValue(xpath + '/velocity/translationalMovingWall/velocity/x', self._ui.xVelocity.text(),
                                self.tr('X-Velocity'))
                    db.setValue(xpath + '/velocity/translationalMovingWall/velocity/y', self._ui.yVelocity.text(),
                                self.tr('Y-Velocity'))
                    db.setValue(xpath + '/velocity/translationalMovingWall/velocity/z', self._ui.zVelocity.text(),
                                self.tr('Z-Velocity'))
                elif velocityCondition == WallVelocityCondition.ROTATIONAL_MOVING_WALL:
                    db.setValue(xpath + '/velocity/rotationalMovingWall/speed', self._ui.speed.text(), self.tr('Speed'))
                    db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/x',
                                self._ui.rotationAxisX.text(), self.tr('Rotation-Axis Origin X'))
                    db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/y',
                                self._ui.rotationAxisY.text(), self.tr('Rotation-Axis Origin Y'))
                    db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/z',
                                self._ui.rotationAxisZ.text(), self.tr('Rotation-Axis Origin Z'))
                    db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/x',
                                self._ui.rotationDirectionX.text(), self.tr('Rotation-Axis Direction X'))
                    db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/y',
                                self._ui.rotationDirectionY.text(), self.tr('Rotation-Axis Direction Y'))
                    db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/z',
                                self._ui.rotationDirectionZ.text(), self.tr('Rotation-Axis Direction Z'))

                if ModelsDB.isEnergyModelOn():
                    temparatureType = WallTemperature(self._ui.temperatureType.currentData())
                    db.setValue(xpath + '/temperature/type', temparatureType.value)
                    if temparatureType == WallTemperature.CONSTANT_TEMPERATURE:
                        db.setValue(xpath + '/temperature/temperature', self._ui.temperature.text(),
                                    self.tr('Temperature'))
                    elif temparatureType == WallTemperature.CONSTANT_HEAT_FLUX:
                        db.setValue(xpath + '/temperature/heatFlux', self._ui.heatFlux.text(), self.tr('Heat Flux'))
                    elif temparatureType == WallTemperature.CONVECTION:
                        db.setValue(xpath + '/temperature/heatTransferCoefficient',
                                    self._ui.heatTransferCoefficient.text(), self.tr('Heat Transfer Coefficient'))
                        db.setValue(xpath + '/temperature/freeStreamTemperature', self._ui.freeStreamTemperature.text(),
                                    self.tr('Free Stream Temperature'))
                        db.setValue(xpath + '/temperature/externalEmissivity', self._ui.externalEmissivity.text(),
                                    self.tr('External Emissivity'))
                        if not await self._wallLayersWidget.updateDB(db):
                            return

                if self._ui.contactAngleGroup.isVisible():
                    contactAngleModel = ContactAngleModel(self._ui.contactAngleModel.currentData())
                    db.setValue(xpath + '/wallAdhesions/model', contactAngleModel.value)
                    if self._ui.contactAngleFormLayout.isRowVisible(self._ui.contactAngleLimit):
                        contactAngleLimit = ContactAngleLimit(self._ui.contactAngleLimit.currentData())
                        db.setValue(xpath + '/wallAdhesions/limit', contactAngleLimit.value)

                    if contactAngleModel == ContactAngleModel.CONSTANT:
                        for i in range(self._constantContactAngles.count()):
                            mid1, mid2, name1, name2, [ca] = self._constantContactAngles.row(i)
                            caxpath = f'{xpath}/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'
                            db.setValue(caxpath + '/contactAngle', ca, self.tr(f'Constant Angle of ({name1}, {name2})'))
                    elif contactAngleModel == ContactAngleModel.DYNAMIC:
                        for i in range(self._constantContactAngles.count()):
                            mid1, mid2, name1, name2, [ca1, ca2, ca3, scale] = self._dynamicContactAngles.row(i)
                            caxpath = f'{xpath}/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'
                            db.setValue(caxpath + '/contactAngle', ca1, self.tr(f'Equilibrium CA of ({name1}, {name2})'))
                            db.setValue(caxpath + '/advancingContactAngle', ca2,
                                        self.tr(f'Advancing CA of ({name1}, {name2})'))
                            db.setValue(caxpath + '/recedingContactAngle', ca3,
                                        self.tr(f'Receding CA of ({name1}, {name2})'))
                            db.setValue(caxpath + '/characteristicVelocityScale', scale,
                                        self.tr(f'Characteristic Velocity Scale of ({name1}, {name2})'))

                if ModelsDB.isRadiationModelOn():
                    db.setValue(xpath + '/radiation/wallEmissivity', self._ui.wallEmissivity.text(),
                                  self.tr('Wall Emissivity'))
                    db.setValue(xpath + '/radiation/radiativeFluxRelaxation', self._ui.radiativeFluxRelaxation.text(),
                                  self.tr('Radiative Flux Relaxation'))
                super().accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))

    def _connectSignalsSlots(self):
        self._ui.velocityCondition.currentIndexChanged.connect(self._velocityConditionChanged)
        self._ui.temperatureType.currentIndexChanged.connect(self._temperatureTypeChanged)
        self._ui.contactAngleModel.currentIndexChanged.connect(self._contactAngleTypeChanged)

    def _load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.velocityCondition.setCurrentIndex(
            self._ui.velocityCondition.findData(WallVelocityCondition(db.getValue(xpath + '/velocity/type'))))
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
            self._wallLayersWidget = WallLayersWidget(self, self._ui, xpath + '/temperature/wallLayers')
            self._ui.temperatureType.setCurrentIndex(
                self._ui.temperatureType.findData(WallTemperature(db.getValue(xpath + '/temperature/type'))))
            self._ui.temperature.setText(db.getValue(xpath + '/temperature/temperature'))
            self._ui.heatFlux.setText(db.getValue(xpath + '/temperature/heatFlux'))
            self._ui.heatTransferCoefficient.setText(db.getValue(xpath + '/temperature/heatTransferCoefficient'))
            self._ui.freeStreamTemperature.setText(db.getValue(xpath + '/temperature/freeStreamTemperature'))
            self._ui.externalEmissivity.setText(db.getValue(xpath + '/temperature/externalEmissivity'))
            self._wallLayersWidget.load()
            self._temperatureTypeChanged()
        else:
            self._ui.temperatureGroup.hide()

        rname = BoundaryDB.getBoundaryRegion(self._bcid)
        secondaryMaterials = RegionDB.getSecondaryMaterials(rname) if ModelsDB.isMultiphaseModelOn() else None
        if secondaryMaterials:
            self._phases = len(secondaryMaterials) + 1
            self._loadContactAngles(rname, secondaryMaterials)
            self._setupContactAngleModelCombo()
            self._ui.contactAngleModel.setCurrentIndex(
                self._ui.contactAngleModel.findData(ContactAngleModel(db.getValue(xpath + '/wallAdhesions/model'))))

            if self._phases == 2:
                self._setupContactAngleLimitCombo()
                self._ui.contactAngleLimit.setCurrentIndex(
                    self._ui.contactAngleLimit.findData(ContactAngleLimit(db.getValue(xpath + '/wallAdhesions/limit'))))
        else:
            self._ui.contactAngleGroup.hide()

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
        self._ui.velocityCondition.addItem(self.tr('No Slip'), WallVelocityCondition.NO_SLIP)
        self._ui.velocityCondition.addItem(self.tr('Slip'), WallVelocityCondition.SLIP)
        self._ui.velocityCondition.addItem(self.tr('Moving Wall'), WallVelocityCondition.MOVING_WALL)
        if not GeneralDB.isCompressible() and not ModelsDB.isMultiphaseModelOn():
            self._ui.velocityCondition.addItem(self.tr('Atmospheric Wall'), WallVelocityCondition.ATMOSPHERIC_WALL)
        self._ui.velocityCondition.addItem(self.tr('Translational Moving Wall'),
                                           WallVelocityCondition.TRANSLATIONAL_MOVING_WALL)
        self._ui.velocityCondition.addItem(self.tr('Rotational Moving Wall'),
                                           WallVelocityCondition.ROTATIONAL_MOVING_WALL)

    def _setupTemperatureCombo(self):
        self._ui.temperatureType.addItem(self.tr('Adiabatic'), WallTemperature.ADIABATIC)
        self._ui.temperatureType.addItem(self.tr('Constant Temperature'), WallTemperature.CONSTANT_TEMPERATURE)
        self._ui.temperatureType.addItem(self.tr('Constant Heat Flux'), WallTemperature.CONSTANT_HEAT_FLUX)
        self._ui.temperatureType.addItem(self.tr('Convection and Radiation'), WallTemperature.CONVECTION)

    def _setupContactAngleModelCombo(self):
        self._ui.contactAngleModel.addItem(self.tr('Disable'), ContactAngleModel.DISABLE)
        self._ui.contactAngleModel.addItem(self.tr('Constant'), ContactAngleModel.CONSTANT)
        self._ui.contactAngleModel.addItem(self.tr('Dynamic'), ContactAngleModel.DYNAMIC)

    def _setupContactAngleLimitCombo(self):
        self._ui.contactAngleLimit.addItem(self.tr('None'), ContactAngleLimit.NONE)
        self._ui.contactAngleLimit.addItem(self.tr('Gradient'), ContactAngleLimit.GRADIENT)
        self._ui.contactAngleLimit.addItem(self.tr('Zero Gradient'), ContactAngleLimit.ZERO_GRADIENT)
        self._ui.contactAngleLimit.addItem(self.tr('Alpha'), ContactAngleLimit.ALPHA)

    def _velocityConditionChanged(self):
        velocityCondition = WallVelocityCondition(self._ui.velocityCondition.currentData())

        self._ui.translationalMovingWall.setVisible(
            velocityCondition == WallVelocityCondition.TRANSLATIONAL_MOVING_WALL)
        self._ui.rotationalMovingWall.setVisible(velocityCondition == WallVelocityCondition.ROTATIONAL_MOVING_WALL)

    def _temperatureTypeChanged(self):
        temparatureType = WallTemperature(self._ui.temperatureType.currentData())

        self._ui.constantTemperature.setVisible(temparatureType == WallTemperature.CONSTANT_TEMPERATURE)
        self._ui.constantHeatFlux.setVisible(temparatureType == WallTemperature.CONSTANT_HEAT_FLUX)
        self._ui.convection.setVisible(temparatureType == WallTemperature.CONVECTION)

    def _contactAngleTypeChanged(self):
        contactAngleModel = ContactAngleModel(self._ui.contactAngleModel.currentData())

        self._ui.contactAngleFormLayout.setRowVisible(
            self._ui.contactAngleLimit, contactAngleModel != ContactAngleModel.DISABLE and self._phases == 2)
        self._constantContactAngles.setVisible(contactAngleModel == ContactAngleModel.CONSTANT)
        self._dynamicContactAngles.setVisible(contactAngleModel == ContactAngleModel.DYNAMIC)
