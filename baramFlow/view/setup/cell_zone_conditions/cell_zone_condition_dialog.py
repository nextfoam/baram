#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.cell_zone_db import CellZoneDB, ZoneType, SpecificationMethod
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB, MaterialType
from baramFlow.coredb.models_db import TurbulenceModelHelper, ModelsDB
from baramFlow.coredb.region_db import DEFAULT_REGION_NAME, RegionDB
from .actuator_disk_widget import ActuatorDiskWidget
from .cell_zone_condition_dialog_ui import Ui_CellZoneConditionDialog
from .constant_source_widget import ConstantSourceWidget
from .fixed_value_widget import FixedValueWidget
from .materials_widget import MaterialsWidget
from .MRF_widget import MRFWidget
from .porous_zone_widget import PorousZoneWidget
from .sliding_mesh_widget import SlidingMeshWidget
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
        self._db = coredb.CoreDB()
        self._xpath = CellZoneDB.getXPath(self._czid)
        self._name = self._db.getValue(self._xpath + '/name')

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

        self._materialSourceTermsLayout = None
        self._specieFixedValuesLayout = None

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

            self._materialsWidget = MaterialsWidget(self._rname, isMultiPhaseOn)
            if isMultiPhaseOn:
                self._materialsWidget.materialsChanged.connect(self._setupMaterialSourceWidgets)
            elif isSpeciesOn:
                self._materialsWidget.materialsChanged.connect(self._setupSpeciesWidgets)
            layout.addWidget(self._materialsWidget)

            if self._rname:
                self._ui.zoneName.setText(self._rname)
            else:
                self._ui.zoneName.setText(DEFAULT_REGION_NAME)
        else:
            self._rname = CellZoneDB.getCellZoneRegion(self._czid)

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
        layout.addStretch()

        layout = self._ui.sourceTerms.layout()
        if isMultiPhaseOn:
            self._materialSourceTermsLayout = QVBoxLayout()
            layout.addLayout(self._materialSourceTermsLayout)
            self._setupMaterialSourceWidgets(int(RegionDB.getMaterial(self._rname)),
                                             RegionDB.getSecondaryMaterials(self._rname))
        elif isSpeciesOn:
            self._materialSourceTermsLayout = QVBoxLayout()
            layout.addLayout(self._materialSourceTermsLayout)

            self._specieFixedValuesLayout = QVBoxLayout()
            self._specieFixedValuesLayout.setContentsMargins(0, 0, 0, 0)
            widget = QWidget()
            widget.setLayout(self._specieFixedValuesLayout)
            self._ui.fixedValues.layout().addWidget(widget)

            self._setupSpeciesWidgets(int(RegionDB.getMaterial(self._rname)))
        else:
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
        self._ui.ok.clicked.connect(self._accept)

    def reject(self):
        for mid in self._addedMaterialSourceTerms:
            self._db.removeElement(f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]')

        super().reject()

    @qasync.asyncSlot()
    async def _accept(self):
        writer = CoreDBWriter()

        if CellZoneDB.isRegion(self._name):
            if not self._materialsWidget.appendToWriter(writer):
                return
        else:
            zoneType = self._getZoneTypeRadioValue()
            writer.append(self._xpath + '/zoneType', zoneType, None)

            result = True
            if zoneType == ZoneType.MRF.value:
                result = self._MRFZone.appendToWriter(writer)
            elif zoneType == ZoneType.POROUS.value:
                result = self._porousZone.appendToWriter(writer)
            elif zoneType == ZoneType.SLIDING_MESH.value:
                result = self._slidingMeshZone.appendToWriter(writer)
            elif zoneType == ZoneType.ACTUATOR_DISK.value:
                result = self._actuatorDiskZone.appendToWriter(writer)

            if not result:
                return

        if self._massSourceTerm and not self._massSourceTerm.appendToWriter(writer):
            return

        if ModelsDB.isMultiphaseModelOn():
            for mid, widget in self._materialSourceTerms.items():
                if mid in self._secondaryMaterials:
                    self._materialSourceTerms[mid].appendToWriter(writer)
                else:
                    self._db.removeElement(f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]')

        elif ModelsDB.isSpeciesModelOn():
            if self._species:
                for mid, widget in self._materialSourceTerms.items():
                    if mid in self._species:
                        self._materialSourceTerms[mid].appendToWriter(writer)
                    else:
                        self._db.removeElement(f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]')
            else:
                self._db.clearElement(f'{self._xpath}/sourceTerms/materials')

        if self._energySourceTerm and not self._energySourceTerm.appendToWriter(writer):
            return

        for field, widget in self._turbulenceSourceTerms.items():
            if not widget.appendToWriter(writer):
                return

        for field, widget in self._scalarSourceTerms.items():
            if not widget.appendToWriter(writer):
                return

        if self._ui.velocityGroup.isChecked():
            writer.setAttribute(self._xpath + 'fixedValues/velocity', 'disabled', 'false')
            writer.append(self._xpath + '/fixedValues/velocity/velocity/x',
                          self._ui.xVelocity.text(), self.tr("X-Velocity"))
            writer.append(self._xpath + '/fixedValues/velocity/velocity/y',
                          self._ui.yVelocity.text(), self.tr("Y-Velocity"))
            writer.append(self._xpath + '/fixedValues/velocity/velocity/z',
                          self._ui.zVelocity.text(), self.tr("Z-Velocity"))
            writer.append(self._xpath + '/fixedValues/velocity/relaxation',
                          self._ui.relaxation.text(), self.tr("relaxation"))
        else:
            writer.setAttribute(self._xpath + 'fixedValues/velocity', 'disabled', 'true')

        if self._temperature and not self._temperature.appendToWriter(writer):
            return

        for field, widget in self._turbulenceFixedValues.items():
            if not widget.appendToWriter(writer):
                return

        for field, widget in self._scalarFixedValues.items():
            if not widget.appendToWriter(writer):
                return

        if ModelsDB.isSpeciesModelOn() and MaterialDB.getType(self._material):
            for mid, _ in self._db.getSpecies(self._material):
                if not self._specieFixedValueWidgets[mid].appendToWriter(writer):
                    return

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            # self._db.print()
            self.accept()

    def _load(self):
        self._getZoneTypeRadio(self._db.getValue(self._xpath + '/zoneType')).setChecked(True)

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

        if self._massSourceTerm:
            self._massSourceTerm.load()

        for field, widget in self._turbulenceSourceTerms.items():
            widget.load()

        for field, widget in self._scalarSourceTerms.items():
            widget.load()

        self._ui.velocityGroup.setChecked(
            self._db.getAttribute(self._xpath + '/fixedValues/velocity', 'disabled') == 'false')
        self._ui.xVelocity.setText(self._db.getValue(self._xpath + '/fixedValues/velocity/velocity/x'))
        self._ui.yVelocity.setText(self._db.getValue(self._xpath + '/fixedValues/velocity/velocity/y'))
        self._ui.zVelocity.setText(self._db.getValue(self._xpath + '/fixedValues/velocity/velocity/z'))
        self._ui.relaxation.setText(self._db.getValue(self._xpath + '/fixedValues/velocity/relaxation'))

        if ModelsDB.isEnergyModelOn():
            self._energySourceTerm.load()
            self._temperature.load()

        for field, widget in self._turbulenceFixedValues.items():
            widget.load()

        for field, widget in self._scalarFixedValues.items():
            widget.load()

    def _setupTurbulenceWidgets(self):
        sourceTermsLayout = self._ui.sourceTerms.layout()
        fixedValuesLayout = self._ui.fixedValues.layout()

        for field in TurbulenceModelHelper.getFields():
            self._turbulenceSourceTerms[field] = ConstantSourceWidget(
                f'{field.name()}, {field.symbol}', field.symbol, field.sourceUnits,
                self._xpath + '/sourceTerms/' + field.xpathName)
            sourceTermsLayout.addWidget(self._turbulenceSourceTerms[field])

            self._turbulenceFixedValues[field] = FixedValueWidget(
                f'{field.name()}, {field.symbol}', f'{field.symbol} ({field.unit})',
                self._xpath + '/fixedValues/' + field.xpathName)
            fixedValuesLayout.addWidget(self._turbulenceFixedValues[field])

    def _setupScalarWidgets(self):
        sourceTermsLayout = self._ui.sourceTerms.layout()
        fixedValuesLayout = self._ui.fixedValues.layout()

        for scalarID, fieldName in self._db.getUserDefinedScalarsInRegion(self._rname):
            xpath = self._xpath + f'/sourceTerms/userDefinedScalars/scalarSource[scalarID="{scalarID}"]'
            # if not self._db.exists(xpath):
            #     CellZoneDB.addScalarSourceTerm(self._czid, scalarID)

            self._scalarSourceTerms[scalarID] = VariableSourceWidget(fieldName, xpath)
            sourceTermsLayout.addWidget(self._scalarSourceTerms[scalarID])

            xpath = self._xpath + f'/fixedValues/userDefinedScalars/scalar[scalarID="{scalarID}"]/value'
            # if not self._db.exists(xpath):
            #     CellZoneDB.addScalarFixedValue(self._czid, scalarID)

            self._scalarFixedValues[scalarID] = FixedValueWidget(fieldName, fieldName, xpath)
            fixedValuesLayout.addWidget(self._scalarFixedValues[scalarID])

    def _setupMaterialSourceWidgets(self, primary, secondaries):
        for mid in self._secondaryMaterials:
            if mid not in secondaries:
                self._materialSourceTerms[mid].hide()
                self._materialSourceTerms[mid].setChecked(False)

        for mid in secondaries:
            if mid in self._materialSourceTerms:
                self._materialSourceTerms[mid].show()
            else:
                xpath = f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]'
                if not self._db.exists(xpath):
                    self._db.addElementFromString(self._xpath + '/sourceTerms/materials',
                                                  CellZoneDB.buildMaterialSourceTermElement(mid))
                    self._addedMaterialSourceTerms.append(mid)

                widget = VariableSourceWidget(MaterialDB.getName(mid), xpath)
                self._materialSourceTerms[mid] = widget
                self._materialSourceTermsLayout.addWidget(widget)
                widget.load()

        self._material = primary
        self._secondaryMaterials = secondaries

    def _setupSpeciesWidgets(self, primary):
        if self._material == primary:
            return

        for mid, widget in self._materialSourceTerms.items():
            widget.hide()
            widget.setChecked(False)

        for mid, widget in self._specieFixedValueWidgets.items():
            widget.hide()
            widget.setChecked(False)

        self._material = primary

        if MaterialDB.getType(self._material) != MaterialType.MIXTURE:
            self._species = None
            return

        mixture = MaterialDB.getName(self._material)
        species = self._db.getSpecies(self._material)
        self._species = []

        for mid, name in species:
            self._species.append(mid)

            if mid in self._materialSourceTerms:
                self._materialSourceTerms[mid].show()
            else:
                xpath = f'{self._xpath}/sourceTerms/materials/materialSource[material="{mid}"]'
                if not self._db.exists(xpath):
                    self._db.addElementFromString(self._xpath + '/sourceTerms/materials',
                                                  CellZoneDB.buildMaterialSourceTermElement(mid))
                    self._addedMaterialSourceTerms.append(mid)

                widget = VariableSourceWidget(name, xpath)
                self._materialSourceTerms[mid] = widget
                self._materialSourceTermsLayout.addWidget(widget)
                widget.load()

            if mid in self._specieFixedValueWidgets:
                self._specieFixedValueWidgets[mid].show()
            else:
                # widget = SpeciesFixedValueWidget(self._czid, self._material, species, CellZoneDB.isRegion(self._name))
                widget = FixedValueWidget(
                    f'{mixture}.{name}', name,
                    f'{self._xpath}/fixedValues/species/mixture[mid="{self._material}"]/specie[mid="{mid}"]/value')
                self._specieFixedValueWidgets[mid] = widget
                self._specieFixedValuesLayout.addWidget(widget)
                widget.load()

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
