#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel

from widgets.async_message_box import AsyncMessageBox
from widgets.enum_button_group import EnumButtonGroup

from baramFlow.base.boundary.boundary import BoundaryManager
from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import boolToDBText
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.boundary_db import BoundaryDB, WallTemperature, ContactAngleModel, ContactAngleLimit
from baramFlow.coredb.boundary_db import WallMotion, ShearCondition, MovingWallMotion
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.view.widgets.batchable_float_edit import BatchableFloatEdit
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .wall_dialog_ui import Ui_WallDialog
from .patch_interaction_widget import PatchInteractionWidget


class ContactAnglesWidget(QWidget):
    def __init__(self, parent, labels, names):
        super().__init__()
        self._rows = []

        self._names = names

        self._layout = QGridLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        parent.layout().addWidget(self)

        column = 2
        for label in labels:
            self._layout.addWidget(QLabel(label), 0, column)
            column += 1

    def addRow(self, mid1, mid2, name1, name2, values):
        row = self._layout.count()

        self._layout.addWidget(QLabel(name1), row, 0)
        self._layout.addWidget(QLabel(name2), row, 1)

        editors = []
        column = 2
        for v in values:
            e = BatchableFloatEdit(v)
            editors.append(e)
            self._layout.addWidget(e, row, column)
            column += 1

        self._rows.append((mid1, mid2, name1, name2, editors))

    def count(self):
        return len(self._rows)

    def row(self, index):
        mid1, mid2, name1, name2, editors = self._rows[index]
        return mid1, mid2, name1, name2, [e.text() for e in editors]

    def validate(self):
        for i in range(self.count()):
            _, _, _, _, editors = self._rows[i]
            for j in range(len(editors)):
                editors[j].validate(self._names[j])

class WallDialog(ResizableDialog):
    RELATIVE_XPATH = '/wall'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_WallDialog()
        self._ui.setupUi(self)

        self._bcid = bcid

        self._phases = 1

        self._wallMotionRadios = EnumButtonGroup()
        self._shearConditionRadios = EnumButtonGroup()

        self._constantContactAngles = None
        self._dynamicContactAngles = None

        self._patchInteractionWidget = None

        self._xpath = BoundaryDB.getXPath(bcid)

        self._wallMotionRadios.addEnumButton(self._ui.stationaryWall,   WallMotion.STATIONARY_WALL)
        self._wallMotionRadios.addEnumButton(self._ui.movingWall,       WallMotion.MOVING_WALL)

        self._ui.atmosphericWall.setEnabled(not GeneralDB.isCompressible() and not ModelsDB.isMultiphaseModelOn())

        self._ui.movingWallMotion.addItem(self.tr('Translational Motion'),  MovingWallMotion.TRANSLATIONAL_MOTION)
        self._ui.movingWallMotion.addItem(self.tr('Rotational Motion'),     MovingWallMotion.ROTATIONAL_MOTION)
        self._ui.movingWallMotion.addItem(self.tr('Mesh Motion'),           MovingWallMotion.MESH_MOTION)

        self._shearConditionRadios.addEnumButton(self._ui.noSlip,   ShearCondition.NO_SLIP)
        self._shearConditionRadios.addEnumButton(self._ui.slip,     ShearCondition.SLIP)

        if DPMModelManager.isModelOn():
            self._patchInteractionWidget = PatchInteractionWidget(self._bcid)
            self._ui.dialogContents.layout().addWidget(self._patchInteractionWidget)

        self._connectSignalsSlots()

        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        wallMotion = self._wallMotionRadios.checkedData()
        movingMotion = self._ui.movingWallMotion.currentData()
        wallRoughnessEnabled = (not (self._ui.stationaryWall.isChecked() and self._ui.atmosphericWall.isChecked())
                                and self._ui.noSlip.isChecked())
        temparatureType = self._ui.temperatureType.currentData()
        contactAngleModel = self._ui.contactAngleModel.currentData()

        try:
            if wallMotion == WallMotion.MOVING_WALL:
                if movingMotion == MovingWallMotion.TRANSLATIONAL_MOTION:
                    self._ui.xVelocity.validate(self.tr('X-Velocity'))
                    self._ui.xVelocity.validate(self.tr('Y-Velocity'))
                    self._ui.xVelocity.validate(self.tr('Z-Velocity'))
                elif movingMotion == MovingWallMotion.ROTATIONAL_MOTION:
                    self._ui.speed.validate(self.tr('Speed'))
                    self._ui.rotationAxisOriginX.validate(self.tr('Rotation-Axis X'))
                    self._ui.rotationAxisOriginY.validate(self.tr('Rotation-Axis Y'))
                    self._ui.rotationAxisOriginZ.validate(self.tr('Rotation-Axis Z'))
                    self._ui.rotationDirectionX.validate(self.tr('Rotation-Axis X'))
                    self._ui.rotationDirectionY.validate(self.tr('Rotation-Axis Y'))
                    self._ui.rotationDirectionZ.validate(self.tr('Rotation-Axis Z'))

            if wallRoughnessEnabled:
                self._ui.roughnessHeight.validate(self.tr('Wall Roughness Height'), low=0)
                self._ui.roughnessConstant.validate(self.tr('Wall Roughness Constant'), low=0.5, high=1)

            if temparatureType == WallTemperature.CONSTANT_TEMPERATURE:
                self._ui.temperature.validate(self.tr('Temperature'))
            elif temparatureType == WallTemperature.CONSTANT_HEAT_FLUX:
                self._ui.heatFlux.validate(self.tr('Heat Flux'))
            elif temparatureType == WallTemperature.CONVECTION:
                self._ui.heatTransferCoefficient.validate(self.tr('Heat Transfer Coefficient'))
                self._ui.freeStreamTemperature.validate(self.tr('Free Stream Temperature'))
                self._ui.externalEmissivity.validate(self.tr('External Emissivity'))
                self._ui.wallLayers.validate()

            if self._ui.contactAngleGroup.isVisible():
                if contactAngleModel == ContactAngleModel.CONSTANT:
                    self._constantContactAngles.validate()
                elif contactAngleModel == ContactAngleModel.DYNAMIC:
                    self._dynamicContactAngles.validate()

            if ModelsDB.isRadiationModelOn():
                self._ui.wallEmissivity.validate(self.tr('Wall Emissivity'), low=0, high=1)
                self._ui.radiativeFluxRelaxation.validate(self.tr('Radiative Flux Relaxation'), low=0, high=1)

            if self._patchInteractionWidget is not None:
                self._patchInteractionWidget.validate()
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        xpath = self._xpath + self.RELATIVE_XPATH
        try:
            with coredb.CoreDB() as db:
                db.setValue(xpath + '/velocity/wallMotion/type', wallMotion.value)
                if wallMotion == WallMotion.STATIONARY_WALL:
                    db.setValue(xpath + '/velocity/wallMotion/stationaryWall/atmosphericWall',
                                boolToDBText(self._ui.atmosphericWall.isChecked()))
                else:
                    db.setValue(xpath + '/velocity/wallMotion/movingWall/motion', movingMotion.value)

                    if movingMotion == MovingWallMotion.TRANSLATIONAL_MOTION:
                        db.setValue(xpath + '/velocity/translationalMovingWall/velocity/x', self._ui.xVelocity.text())
                        db.setValue(xpath + '/velocity/translationalMovingWall/velocity/y', self._ui.yVelocity.text())
                        db.setValue(xpath + '/velocity/translationalMovingWall/velocity/z', self._ui.zVelocity.text())
                    elif movingMotion == MovingWallMotion.ROTATIONAL_MOTION:
                        db.setValue(xpath + '/velocity/rotationalMovingWall/speed', self._ui.speed.text())
                        db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/x',
                                    self._ui.rotationAxisOriginX.text())
                        db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/y',
                                    self._ui.rotationAxisOriginY.text())
                        db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/z',
                                    self._ui.rotationAxisOriginZ.text())
                        db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/x',
                                    self._ui.rotationDirectionX.text())
                        db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/y',
                                    self._ui.rotationDirectionY.text())
                        db.setValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/z',
                                    self._ui.rotationDirectionZ.text())

                db.setValue(xpath + '/velocity/shearCondition', self._shearConditionRadios.checkedData().value)

                if wallRoughnessEnabled:
                    db.setValue(xpath + '/velocity/wallRoughness/height', self._ui.roughnessHeight.text())
                    db.setValue(xpath + '/velocity/wallRoughness/constant', self._ui.roughnessConstant.text())

                if ModelsDB.isEnergyModelOn():
                    db.setValue(xpath + '/temperature/type', temparatureType.value)
                    if temparatureType == WallTemperature.CONSTANT_TEMPERATURE:
                        db.setValue(xpath + '/temperature/temperature', self._ui.temperature.text())
                    elif temparatureType == WallTemperature.CONSTANT_HEAT_FLUX:
                        db.setValue(xpath + '/temperature/heatFlux', self._ui.heatFlux.text())
                    elif temparatureType == WallTemperature.CONVECTION:
                        db.setValue(xpath + '/temperature/heatTransferCoefficient',
                                    self._ui.heatTransferCoefficient.text())
                        db.setValue(xpath + '/temperature/freeStreamTemperature', self._ui.freeStreamTemperature.text())
                        db.setValue(xpath + '/temperature/externalEmissivity', self._ui.externalEmissivity.text())
                        await self._ui.wallLayers.updateDB(db, xpath + '/temperature/wallLayers')

                if self._ui.contactAngleGroup.isVisible():
                    contactAngleModel = self._ui.contactAngleModel.currentData()
                    db.setValue(xpath + '/wallAdhesions/model', contactAngleModel.value)
                    if self._ui.contactAngleFormLayout.isRowVisible(self._ui.contactAngleLimit):
                        contactAngleLimit = self._ui.contactAngleLimit.currentData()
                        db.setValue(xpath + '/wallAdhesions/limit', contactAngleLimit.value)

                    if contactAngleModel == ContactAngleModel.CONSTANT:
                        for i in range(self._constantContactAngles.count()):
                            mid1, mid2, name1, name2, [ca] = self._constantContactAngles.row(i)
                            caxpath = f'{xpath}/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'
                            db.setValue(caxpath + '/contactAngle', ca)
                    elif contactAngleModel == ContactAngleModel.DYNAMIC:
                        for i in range(self._dynamicContactAngles.count()):
                            mid1, mid2, name1, name2, [ca1, ca2, ca3, scale] = self._dynamicContactAngles.row(i)
                            caxpath = f'{xpath}/wallAdhesions/wallAdhesion[mid="{mid1}"][mid="{mid2}"]'
                            db.setValue(caxpath + '/contactAngle', ca1)
                            db.setValue(caxpath + '/advancingContactAngle', ca2)
                            db.setValue(caxpath + '/recedingContactAngle', ca3)
                            db.setValue(caxpath + '/characteristicVelocityScale', scale)

                if ModelsDB.isRadiationModelOn():
                    db.setValue(xpath + '/radiation/wallEmissivity', self._ui.wallEmissivity.text())
                    db.setValue(xpath + '/radiation/radiativeFluxRelaxation', self._ui.radiativeFluxRelaxation.text())

                if self._patchInteractionWidget is not None:
                    BoundaryManager.updatePatchInteraction(db, self._bcid, self._patchInteractionWidget.updateData())

                self.accept()
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))

    def _connectSignalsSlots(self):
        self._wallMotionRadios.dataChecked.connect(self._wallMotionChanged)
        self._ui.atmosphericWall.stateChanged.connect(self._atomospericWallToggled)
        self._ui.movingWallMotion.currentIndexChanged.connect(self._updateMovingWallParameters)
        self._shearConditionRadios.dataChecked.connect(self._updateRoughnessEnabled)
        self._ui.temperatureType.currentIndexChanged.connect(self._temperatureTypeChanged)
        self._ui.contactAngleModel.currentIndexChanged.connect(self._contactAngleTypeChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._wallMotionRadios.setCheckedData(WallMotion(db.getValue(xpath + '/velocity/wallMotion/type')))
        self._ui.atmosphericWall.setChecked(db.getBool(xpath + '/velocity/wallMotion/stationaryWall/atmosphericWall'))
        self._ui.movingWallMotion.setCurrentIndex(
            self._ui.movingWallMotion.findData(
                MovingWallMotion(db.getValue(xpath + '/velocity/wallMotion/movingWall/motion'))))
        self._shearConditionRadios.setCheckedData(ShearCondition(db.getValue(xpath + '/velocity/shearCondition')))
        self._ui.roughnessHeight.setText(db.getValue(xpath + '/velocity/wallRoughness/height'))
        self._ui.roughnessConstant.setText(db.getValue(xpath + '/velocity/wallRoughness/constant'))

        self._ui.xVelocity.setText(db.getValue(xpath + '/velocity/translationalMovingWall/velocity/x'))
        self._ui.yVelocity.setText(db.getValue(xpath + '/velocity/translationalMovingWall/velocity/y'))
        self._ui.zVelocity.setText(db.getValue(xpath + '/velocity/translationalMovingWall/velocity/z'))
        self._ui.speed.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/speed'))
        self._ui.rotationAxisOriginX.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/x'))
        self._ui.rotationAxisOriginY.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/y'))
        self._ui.rotationAxisOriginZ.setText(db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisOrigin/z'))
        self._ui.rotationDirectionX.setText(
            db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/x'))
        self._ui.rotationDirectionY.setText(
            db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/y'))
        self._ui.rotationDirectionZ.setText(
            db.getValue(xpath + '/velocity/rotationalMovingWall/rotationAxisDirection/z'))

        if ModelsDB.isEnergyModelOn():
            self._setupTemperatureCombo()
            self._ui.temperatureType.setCurrentIndex(
                self._ui.temperatureType.findData(WallTemperature(db.getValue(xpath + '/temperature/type'))))
            self._ui.temperature.setText(db.getValue(xpath + '/temperature/temperature'))
            self._ui.heatFlux.setText(db.getValue(xpath + '/temperature/heatFlux'))
            self._ui.heatTransferCoefficient.setText(db.getValue(xpath + '/temperature/heatTransferCoefficient'))
            self._ui.freeStreamTemperature.setText(db.getValue(xpath + '/temperature/freeStreamTemperature'))
            self._ui.externalEmissivity.setText(db.getValue(xpath + '/temperature/externalEmissivity'))
            self._ui.wallLayers.load(xpath + '/temperature/wallLayers')
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

        if self._patchInteractionWidget is not None:
            self._patchInteractionWidget.setData(BoundaryManager.patchInteraction(self._bcid))


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
            self._ui.contactAngleGroup, [self.tr('Constant Angle (degree)')], [self.tr('Constant Angle')])
        self._dynamicContactAngles = ContactAnglesWidget(self._ui.contactAngleGroup,
                                                         [self.tr('Equilibrium CA\n (deg)'),
                                                          self.tr('Advancing CA\n (deg)'),
                                                          self.tr('Receding CA\n (deg)'),
                                                          self.tr('Characteristic Velocity Scale\n (m/s)')],
                                                         [self.tr('Equilibrium CA'),
                                                          self.tr('Advancing CA'),
                                                          self.tr('Receding CA'),
                                                          self.tr('Characteristic Velocity Scale')])

        mid = RegionDB.getMaterial(rname)
        materials = {mid: MaterialDB.getName(mid)}

        count = len(secondaryMaterials)
        for i in range(count):
            materials[secondaryMaterials[i]] = MaterialDB.getName(secondaryMaterials[i])
            addAdhesionRows(mid, secondaryMaterials[i])

        for i in range(count):
            for j in range(i + 1, count):
                addAdhesionRows(secondaryMaterials[i], secondaryMaterials[j])

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

    def _wallMotionChanged(self, motion):
        if motion == WallMotion.STATIONARY_WALL:
            self._ui.atmosphericWall.setEnabled(True)
            self._ui.movingWallMotion.setEnabled(False)
        elif motion == WallMotion.MOVING_WALL:
            self._ui.noSlip.setChecked(True)
            self._ui.atmosphericWall.setEnabled(False)
            self._ui.movingWallMotion.setEnabled(True)

        self._updateShearConditionEnabled()
        self._updateRoughnessEnabled()

        self._updateMovingWallParameters()

    def _atomospericWallToggled(self, state):
        if state:
            self._ui.noSlip.setChecked(True)

        self._updateShearConditionEnabled()
        self._updateRoughnessEnabled()

    def _updateMovingWallParameters(self):
        if self._wallMotionRadios.checkedData() == WallMotion.MOVING_WALL:
            movingMotion = self._ui.movingWallMotion.currentData()
            self._ui.translationalMovingWall.setVisible(movingMotion == MovingWallMotion.TRANSLATIONAL_MOTION)
            self._ui.rotationalMovingWall.setVisible(movingMotion == MovingWallMotion.ROTATIONAL_MOTION)
        else:
            self._ui.translationalMovingWall.setVisible(False)
            self._ui.rotationalMovingWall.setVisible(False)

    def _updateShearConditionEnabled(self):
        self._ui.shearCondition.setEnabled(
            self._ui.stationaryWall.isChecked() and not self._ui.atmosphericWall.isChecked())

    def _updateRoughnessEnabled(self):
        self._ui.wallRoughness.setEnabled(
            not (self._ui.stationaryWall.isChecked() and self._ui.atmosphericWall.isChecked())
            and self._ui.noSlip.isChecked())

    def _temperatureTypeChanged(self):
        temparatureType = self._ui.temperatureType.currentData()

        self._ui.constantTemperature.setVisible(temparatureType == WallTemperature.CONSTANT_TEMPERATURE)
        self._ui.constantHeatFlux.setVisible(temparatureType == WallTemperature.CONSTANT_HEAT_FLUX)
        self._ui.convection.setVisible(temparatureType == WallTemperature.CONVECTION)

    def _contactAngleTypeChanged(self):
        contactAngleModel = self._ui.contactAngleModel.currentData()

        self._ui.contactAngleFormLayout.setRowVisible(
            self._ui.contactAngleLimit, contactAngleModel != ContactAngleModel.DISABLE and self._phases == 2)
        self._constantContactAngles.setVisible(contactAngleModel == ContactAngleModel.CONSTANT)
        self._dynamicContactAngles.setVisible(contactAngleModel == ContactAngleModel.DYNAMIC)
