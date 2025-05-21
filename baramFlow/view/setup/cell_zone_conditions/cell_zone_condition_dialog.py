#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from baramFlow.coredb.configuraitions import ConfigurationException
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import CellZoneDB, ZoneType, SpecificationMethod
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import MaterialType
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME, RegionDB
from .actuator_disk_widget import ActuatorDiskWidget
from .cell_zone_condition_dialog_ui import Ui_CellZoneConditionDialog
from .constant_source_widget import ConstantSourceWidget
from .fixed_value_widget import FixedValueWidget
from .materials_widget import MaterialsWidget
from .MRF_widget import MRFWidget
from .porous_zone_widget import PorousZoneWidget
from .sliding_mesh_widget import SlidingMeshWidget
from .turbulence_fields import getTurbulenceFields
from .variable_source_widget import VariableSourceWidget


class CellZoneConditionDialog(QDialog):
    def __init__(self, parent, czid, rname=None):
        super().__init__(parent)
        self._ui = Ui_CellZoneConditionDialog()
        self._ui.setupUi(self)

        self._zoneTypeRadios = {
            self._ui.zoneTypeRadioGroup.id(self._ui.none): ZoneType.NONE.value,
            self._ui.zoneTypeRadioGroup.id(self._ui.MRF): ZoneType.MRF.value,
            self._ui.zoneTypeRadioGroup.id(self._ui.porousZone): ZoneType.POROUS.value,
            self._ui.zoneTypeRadioGroup.id(self._ui.slidingMesh): ZoneType.SLIDING_MESH.value,
            self._ui.zoneTypeRadioGroup.id(self._ui.actuatorDisk): ZoneType.ACTUATOR_DISK.value,
        }

        self._czid = czid
        self._rname = rname
        self._xpath = CellZoneDB.getXPath(self._czid)
        db = coredb.CoreDB()
        self._name = db.getValue(self._xpath + '/name')

        self._material = None
        self._secondaryMaterials = []
        self._species = None

        self._materialsWidget = None

        # Zone Type Widgets
        self._MRFZone = None
        self._porousZone = None
        self._slidingMeshZone = None
        self._actuatorDiskZone = None

        # Source Terms Widgets
        self._massSourceTerm = None
        self._materialSourceTerms = {}
        self._energySourceTerm = None
        self._turbulenceSourceTerms = {}
        self._scalarSourceTerms = {}
        self._specieFixedValueWidgets = {}

        self._materialSourceTermsLayout = QVBoxLayout()
        self._specieFixedValuesLayout = QVBoxLayout()

        self._addedMaterialSourceTerms = []

        # Fixed Value Widgets
        self._turbulenceFixedValues = {}
        self._temperature = None
        self._scalarFixedValues = {}

        isMultiPhaseOn = ModelsDB.isMultiphaseModelOn()
        isSpeciesOn = ModelsDB.isSpeciesModelOn()

        layout = self._ui.setting.layout()
        if CellZoneDB.isRegion(self._name):
            self.setWindowTitle(self.tr('Region Condition'))
            self._ui.zoneType.setVisible(False)

            self._materialsWidget = MaterialsWidget(self._rname)
            layout.addWidget(self._materialsWidget)

            self._ui.zoneName.setText(self._rname if self._rname else DEFAULT_REGION_NAME)
        else:
            self._ui.zoneName.setText(self._name)

            self._MRFZone = MRFWidget(self._xpath)
            layout.addWidget(self._MRFZone)

            self._porousZone = PorousZoneWidget(self._xpath)
            layout.addWidget(self._porousZone)

            if GeneralDB.isTimeTransient():
                self._slidingMeshZone = SlidingMeshWidget(self._xpath)
                layout.addWidget(self._slidingMeshZone)
            else:
                self._ui.slidingMesh.setEnabled(False)

            self._actuatorDiskZone = ActuatorDiskWidget(self._xpath)
            layout.addWidget(self._actuatorDiskZone)

            self._ui.zoneTypeRadioGroup.idToggled.connect(self._zoneTypeChanged)

        if GeneralDB.isCompressibleDensity():
            self._ui.zoneType.setEnabled(False)

        layout.addStretch()

        layout = self._ui.sourceTerms.layout()
        layout.addLayout(self._materialSourceTermsLayout)

        self._specieFixedValuesLayout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget()
        widget.setLayout(self._specieFixedValuesLayout)
        self._ui.fixedValues.layout().addWidget(widget)

        if not isMultiPhaseOn and not isSpeciesOn:
            self._massSourceTerm = VariableSourceWidget(
                self.tr("Mass"), self._xpath + '/sourceTerms/mass', {
                    SpecificationMethod.VALUE_PER_UNIT_VOLUME: 'kg/m<sup>3</sup>s',
                    SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: 'kg/s'
                })
            layout.addWidget(self._massSourceTerm)

        if ModelsDB.isEnergyModelOn():
            self._energySourceTerm = VariableSourceWidget(
                self.tr("Energy"), self._xpath + '/sourceTerms/energy', {
                    SpecificationMethod.VALUE_PER_UNIT_VOLUME: 'W/m<sup>3</sup>',
                    SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: 'W'
                })
            self._ui.sourceTerms.layout().addWidget(self._energySourceTerm)

            self._temperature = FixedValueWidget(
                self.tr("Temperature"), self.tr("Value (K)"), self._xpath + '/fixedValues/temperature')
            self._ui.fixedValues.layout().addWidget(self._temperature)

        self._setupTurbulenceWidgets()
        self._setupScalarWidgets()

        self._ui.sourceTerms.layout().addStretch()
        self._ui.fixedValues.layout().addStretch()

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        if CellZoneDB.isRegion(self._name):
            self._materialsWidget.materialsChanged.connect(self._setMaterials)
        self._ui.ok.clicked.connect(self._accept)

    def reject(self):
        db = coredb.CoreDB()
        for mid in self._addedMaterialSourceTerms:
            db.removeElement(f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]')

        super().reject()

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            with coredb.CoreDB() as db:
                if CellZoneDB.isRegion(self._name):
                    RegionDB.updateMaterials(self._rname, self._material, self._secondaryMaterials)
                    if not self._materialsWidget.updateDB(db):
                        return
                else:
                    zoneType = self._getZoneTypeRadioValue()
                    db.setValue(self._xpath + '/zoneType', zoneType, None)

                    result = True
                    if zoneType == ZoneType.MRF.value:
                        result = self._MRFZone.updateDB(db)
                    elif zoneType == ZoneType.POROUS.value:
                        result = self._porousZone.updateDB(db)
                    elif zoneType == ZoneType.SLIDING_MESH.value:
                        result = self._slidingMeshZone.updateDB(db)
                    elif zoneType == ZoneType.ACTUATOR_DISK.value:
                        result = self._actuatorDiskZone.updateDB(db)

                    if not result:
                        return

                if self._massSourceTerm and not await self._massSourceTerm.updateDB(db):
                    return

                if ModelsDB.isMultiphaseModelOn():
                    for mid, widget in self._materialSourceTerms.items():
                        if mid in self._secondaryMaterials and not await self._materialSourceTerms[mid].updateDB(db):
                            return
                for mid, widget in self._materialSourceTerms.items():
                    if mid in self._species and not await self._materialSourceTerms[mid].updateDB(db):
                        return

                if self._energySourceTerm and not await self._energySourceTerm.updateDB(db):
                    return

                for field, widget in self._turbulenceSourceTerms.items():
                    if not widget.updateDB(db):
                        return

                for field, widget in self._scalarSourceTerms.items():
                    if not await widget.updateDB(db):
                        return

                if self._ui.velocityGroup.isChecked():
                    db.setAttribute(self._xpath + 'fixedValues/velocity', 'disabled', 'false')
                    db.setValue(self._xpath + '/fixedValues/velocity/velocity/x',
                                self._ui.xVelocity.text(), self.tr("X-Velocity"))
                    db.setValue(self._xpath + '/fixedValues/velocity/velocity/y',
                                self._ui.yVelocity.text(), self.tr("Y-Velocity"))
                    db.setValue(self._xpath + '/fixedValues/velocity/velocity/z',
                                self._ui.zVelocity.text(), self.tr("Z-Velocity"))
                    db.setValue(self._xpath + '/fixedValues/velocity/relaxation',
                                self._ui.relaxation.text(), self.tr("relaxation"))
                else:
                    db.setAttribute(self._xpath + 'fixedValues/velocity', 'disabled', 'true')

                if self._temperature and not self._temperature.updateDB(db):
                    return

                for field, widget in self._turbulenceFixedValues.items():
                    if not widget.updateDB(db):
                        return

                for field, widget in self._scalarFixedValues.items():
                    if not widget.updateDB(db):
                        return

                if ModelsDB.isSpeciesModelOn() and MaterialDB.getType(self._material) == MaterialType.MIXTURE:
                    for mid in MaterialDB.getSpecies(self._material):
                        if not self._specieFixedValueWidgets[mid].updateDB(db):
                            return

            self.accept()
        except ConfigurationException as c:
            await AsyncMessageBox().information(self, self.tr("Input Error"), str(c))
        except ValueException as v:
            await AsyncMessageBox().information(self, self.tr("Input Error"), dbErrorToMessage(v))

    def _load(self):
        db = coredb.CoreDB()
        self._getZoneTypeRadio(db.getValue(self._xpath + '/zoneType')).setChecked(True)
        if GeneralDB.isCompressibleDensity():
            self._ui.none.setChecked(True)

        if CellZoneDB.isRegion(self._name):
            if self._materialsWidget:
                self._materialsWidget.load()
            else:
                pass
        else:
            self._MRFZone.load()
            self._porousZone.load()
            if self._slidingMeshZone:
                self._slidingMeshZone.load()
            self._actuatorDiskZone.load()

        self._setMaterials(RegionDB.getMaterial(self._rname), RegionDB.getSecondaryMaterials(self._rname))

        if self._massSourceTerm:
            self._massSourceTerm.load()

        for field, widget in self._turbulenceSourceTerms.items():
            widget.load()

        for field, widget in self._scalarSourceTerms.items():
            widget.load()

        self._ui.velocityGroup.setChecked(
            db.getAttribute(self._xpath + '/fixedValues/velocity', 'disabled') == 'false')
        self._ui.xVelocity.setText(db.getValue(self._xpath + '/fixedValues/velocity/velocity/x'))
        self._ui.yVelocity.setText(db.getValue(self._xpath + '/fixedValues/velocity/velocity/y'))
        self._ui.zVelocity.setText(db.getValue(self._xpath + '/fixedValues/velocity/velocity/z'))
        self._ui.relaxation.setText(db.getValue(self._xpath + '/fixedValues/velocity/relaxation'))

        if ModelsDB.isEnergyModelOn():
            self._energySourceTerm.load()
            self._temperature.load()

        for field, widget in self._turbulenceFixedValues.items():
            widget.load()

        for field, widget in self._scalarFixedValues.items():
            widget.load()

    def _setMaterials(self, primary, secondaries):
        # Clear Source Terms and Fixed Values
        for mid, widget in self._materialSourceTerms.items():
            widget.hide()

        for mid, widget in self._specieFixedValueWidgets.items():
            widget.hide()

        # Setup Material Source Terms for multiphase model
        for mid in secondaries:
            if mid in self._materialSourceTerms:
                self._materialSourceTerms[mid].show()
            else:
                widget = VariableSourceWidget(MaterialDB.getName(mid),
                                              f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]')
                self._materialSourceTerms[mid] = widget
                self._materialSourceTermsLayout.addWidget(widget)
                widget.load()

        # Setup Material Source Terms and Fixed Values for species
        self._species = []
        if MaterialDB.getType(primary) == MaterialType.MIXTURE:
            mixture = MaterialDB.getName(primary)
            species = MaterialDB.getSpecies(primary)

            for mid, name in species.items():
                self._species.append(mid)

                if mid in self._materialSourceTerms:
                    self._materialSourceTerms[mid].show()
                else:
                    widget = VariableSourceWidget(
                        name, f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]', {
                              SpecificationMethod.VALUE_PER_UNIT_VOLUME: 'kg/m<sup>3</sup>s',
                              SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: 'kg/s'})
                    self._materialSourceTerms[mid] = widget
                    self._materialSourceTermsLayout.addWidget(widget)
                    widget.load()

                if mid in self._specieFixedValueWidgets:
                    self._specieFixedValueWidgets[mid].show()
                else:
                    widget = FixedValueWidget(
                        f'{mixture}.{name}', name,
                        f'{self._xpath}/fixedValues/species/mixture[mid="{primary}"]/specie[mid="{mid}"]/value')
                    self._specieFixedValueWidgets[mid] = widget
                    self._specieFixedValuesLayout.addWidget(widget)
                    widget.load()

        self._material = primary
        self._secondaryMaterials = secondaries

    def _setupTurbulenceWidgets(self):
        sourceTermsLayout = self._ui.sourceTerms.layout()
        fixedValuesLayout = self._ui.fixedValues.layout()

        for field in getTurbulenceFields():
            self._turbulenceSourceTerms[field] = ConstantSourceWidget(
                f'{field.name()}, {field.symbol}', field.symbol, field.sourceUnits,
                self._xpath + '/sourceTerms/' + field.xpathName)
            sourceTermsLayout.addWidget(self._turbulenceSourceTerms[field])

            self._turbulenceFixedValues[field] = FixedValueWidget(
                f'{field.name()}, {field.symbol}', f'{field.symbol} ({field.unit})',
                self._xpath + '/fixedValues/' + field.xpathName)
            fixedValuesLayout.addWidget(self._turbulenceFixedValues[field])

    def _setupScalarWidgets(self):
        db = coredb.CoreDB()
        sourceTermsLayout = self._ui.sourceTerms.layout()
        fixedValuesLayout = self._ui.fixedValues.layout()

        for scalarID, fieldName in db.getUserDefinedScalarsInRegion(self._rname):
            xpath = self._xpath + f'/sourceTerms/userDefinedScalars/scalarSource[scalarID="{scalarID}"]'
            self._scalarSourceTerms[scalarID] = VariableSourceWidget(fieldName, xpath)
            sourceTermsLayout.addWidget(self._scalarSourceTerms[scalarID])

            xpath = self._xpath + f'/fixedValues/userDefinedScalars/scalar[scalarID="{scalarID}"]/value'
            self._scalarFixedValues[scalarID] = FixedValueWidget(fieldName, fieldName, xpath)
            fixedValuesLayout.addWidget(self._scalarFixedValues[scalarID])

    def _zoneTypeChanged(self, id_, checked):
        if checked:
            self._MRFZone.setVisible(self._ui.MRF.isChecked())
            self._porousZone.setVisible(self._ui.porousZone.isChecked())
            if self._slidingMeshZone:
                self._slidingMeshZone.setVisible(self._ui.slidingMesh.isChecked())
            self._actuatorDiskZone.setVisible(self._ui.actuatorDisk.isChecked())

    def _getZoneTypeRadio(self, value):
        return self._ui.zoneTypeRadioGroup.button(
            list(self._zoneTypeRadios.keys())[list(self._zoneTypeRadios.values()).index(value)])

    def _getZoneTypeRadioValue(self):
        return self._zoneTypeRadios[self._ui.zoneTypeRadioGroup.id(self._ui.zoneTypeRadioGroup.checkedButton())]
