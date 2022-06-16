#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.setup.models.models_db import TurbulenceModelHelper
from .cell_zone_condition_dialog_ui import Ui_CellZoneConditionDialog
from .mrf_widget import MRFWidget
from .porous_zone_widget import PorousZoneWidget
from .sliding_mesh_widget import SlidingMeshWidget
from .actuator_disk_widget import ActuatorDiskWidget
from .variable_source_widget import VariableSourceWidget
from .constant_source_widget import ConstantSourceWidget
from .fixed_value_widget import FixedValueWidget
from .cell_zone_db import CellZoneDB, ZoneType


class CellZoneConditionDialog(QDialog):
    def __init__(self, parent, rname, czid):
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

        self._rname = rname
        self._czid = czid
        self._db = coredb.CoreDB()
        self._xpath = CellZoneDB.getXPathWithRegion(self._rname, self._czid)

        # Zone Type Widgets
        if self._isAll():
            self._ui.MRF.setEnabled(False)
            self._ui.porousZone.setEnabled(False)
            self._ui.slidingMesh.setEnabled(False)
            self._ui.actuatorDisk.setEnabled(False)
        else:
            self._MRFZone = MRFWidget(self._xpath)
            self._porousZone = PorousZoneWidget(self._xpath)
            self._slidingMeshZone = SlidingMeshWidget(self._xpath)
            self._actuatorDiskZone = ActuatorDiskWidget(self._xpath)

            layout = self._ui.zoneType.layout()
            layout.insertWidget(1, self._MRFZone)
            layout.insertWidget(2, self._porousZone)
            layout.insertWidget(3, self._slidingMeshZone)
            layout.insertWidget(4, self._actuatorDiskZone)

        # Source Terms Widgets
        self._massSourceTerm = VariableSourceWidget(self.tr("Mass"), self._xpath + '/sourceTerms/mass')
        self._energySourceTerm = VariableSourceWidget(self.tr("Energy"), self._xpath + '/sourceTerms/energy')
        self._turbulenceSourceTerms = {}
        self._materialSourceTerms = {}

        layout = self._ui.sourceTerms.layout()
        layout.addWidget(self._massSourceTerm)
        layout.addWidget(self._energySourceTerm)

        # Fixed Value Widgets
        self._xVelocity = FixedValueWidget(
            self.tr("X-Velocity"), self.tr("U<sub>x</sub> (m/s)"), self._xpath + '/fixedValues/xVelocity')
        self._yVelocity = FixedValueWidget(
            self.tr("Y-Velocity"), self.tr("U<sub>y</sub> (m/s)"), self._xpath + '/fixedValues/yVelocity')
        self._zVelocity = FixedValueWidget(
            self.tr("Z-Velocity"), self.tr("U<sub>z</sub> (m/s)"), self._xpath + '/fixedValues/zVelocity')

        layout = self._ui.velocityGroup.layout()
        layout.insertWidget(0, self._xVelocity)
        layout.insertWidget(1, self._yVelocity)
        layout.insertWidget(2, self._zVelocity)

        self._turbulenceFixedValues = {}
        self._temperature = FixedValueWidget(
            self.tr("Temperature"), self.tr("Value (K)"), self._xpath + '/fixedValues/temperature')

        layout = self._ui.fixedValues.layout()
        layout.addWidget(self._temperature)

        self._setupTurbulenceWidgets()
        self._setupMaterialWidgets(["O2"])

        self._ui.zoneType.layout().addStretch()
        self._ui.sourceTerms.layout().addStretch()
        self._ui.fixedValues.layout().addStretch()

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        writer = CoreDBWriter()

        zoneType = self._getZoneTypeRadioValue()
        writer.append(self._xpath + '/zoneType', zoneType, None)
        if zoneType == ZoneType.MRF.value:
            if not self._MRFZone.appendToWriter(writer):
                return
        elif zoneType == ZoneType.POROUS.value:
            self._porousZone.appendToWriter(writer)
        elif zoneType == ZoneType.SLIDING_MESH.value:
            self._slidingMeshZone.appendToWriter(writer)
        elif zoneType == ZoneType.ACTUATOR_DISK.value:
            self._actuatorDiskZone.appendToWriter(writer)

        if not self._massSourceTerm.appendToWriter(writer):
            return
        if not self._energySourceTerm.appendToWriter(writer):
            return
        for field, widget in self._turbulenceSourceTerms.items():
            widget.appendToWriter(writer)

        self._xVelocity.appendToWriter(writer)
        self._yVelocity.appendToWriter(writer)
        self._zVelocity.appendToWriter(writer)
        writer.append(self._xpath + '/fixedValues/relaxation', self._ui.relaxation.text(), self.tr("relaxation"))
        self._temperature.appendToWriter(writer)
        for field, widget in self._turbulenceFixedValues.items():
            widget.appendToWriter(writer)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        self._ui.zoneName.setText(self._db.getValue(self._xpath + '/name'))
        self._getZoneTypeRadio(self._db.getValue(self._xpath + '/zoneType')).setChecked(True)
        if not self._isAll():
            self._MRFZone.load()
            self._porousZone.load()
            self._slidingMeshZone.load()
            self._actuatorDiskZone.load()

        self._massSourceTerm.load()
        self._energySourceTerm.load()
        for field, widget in self._turbulenceSourceTerms.items():
            widget.load()

        self._xVelocity.load()
        self._yVelocity.load()
        self._zVelocity.load()
        self._ui.relaxation.setText(self._db.getValue(self._xpath + '/fixedValues/relaxation'))
        self._temperature.load()
        for field, widget in self._turbulenceFixedValues.items():
            widget.load()

    def _setupTurbulenceWidgets(self):
        sourceTermsLayout = self._ui.sourceTerms.layout()
        fixedValuesLayout = self._ui.fixedValues.layout()
        for field in TurbulenceModelHelper.getFields():
            self._turbulenceSourceTerms[field] = ConstantSourceWidget(
                field.getTitleText(), field.getLabelText(), self._xpath + '/sourceTerms/' + field.xpathName)
            sourceTermsLayout.addWidget(self._turbulenceSourceTerms[field])
            self._turbulenceFixedValues[field] = FixedValueWidget(
                field.getTitleText(), field.getLabelText(), self._xpath + '/fixedValues/' + field.xpathName)
            fixedValuesLayout.addWidget(self._turbulenceFixedValues[field])

    def _setupMaterialWidgets(self, materials):
        layout = self._ui.sourceTerms.layout()
        # for material in materials:
        #     self._materialSourceTerms[material] = VariableSourceWidget(material)
        #     layout.addWidget(self._materialSourceTerms[material])

    def _connectSignalsSlots(self):
        if not self._isAll():
            self._ui.zoneTypeRadioGroup.idToggled.connect(self._zoneTypeChanged)

    def _zoneTypeChanged(self, id_, checked):
        if checked:
            self._MRFZone.setVisible(self._ui.MRF.isChecked())
            self._porousZone.setVisible(self._ui.porousZone.isChecked())
            self._slidingMeshZone.setVisible(self._ui.slidingMesh.isChecked())
            self._actuatorDiskZone.setVisible(self._ui.actuatorDisk.isChecked())

    def _getZoneTypeRadio(self, value):
        return self._ui.zoneTypeRadioGroup.button(
            list(self._zoneTypeRadios.keys())[list(self._zoneTypeRadios.values()).index(value)])

    def _getZoneTypeRadioValue(self):
        return self._zoneTypeRadios[self._ui.zoneTypeRadioGroup.id(self._ui.zoneTypeRadioGroup.checkedButton())]

    def _isAll(self):
        return self._czid == 1
