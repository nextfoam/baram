#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.widgets.resizable_dialog import ResizableDialog
from .cell_zone_condition_dialog_ui import Ui_CellZoneConditionDialog
from .mrf_widget import MRFWidget
from .porous_zone_widget import PorousZoneWidget
from .sliding_mesh_widget import SlidingMeshWidget
from .actuator_disk_widget import ActuatorDiskWidget
from .variable_source_widget import VariableSourceWidget
from .constant_source_widget import ConstantSourceWidget
from .fixed_value_widget import FixedValueWidget


class CellZoneConditionDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_CellZoneConditionDialog()
        self._ui.setupUi(self)

        self._zoneTypeLayout = self._ui.zoneType.layout()
        self._sourceTermsLayout = self._ui.sourceTerms.layout()
        self._fixedValuesLayout = self._ui.fixedValues.layout()

        # Zone Type Widgets
        self._MRFZone = MRFWidget()
        self._porousZone = PorousZoneWidget()
        self._slidingMeshZone = SlidingMeshWidget()
        self._actuatorDiskZone = ActuatorDiskWidget()

        # Source Terms Widgets
        self._massSourceTerm = VariableSourceWidget(self.tr("Mass"))
        self._energySourceTerm = VariableSourceWidget(self.tr("Energy"))
        self._turbulenceSourceTerms = {}
        self._materialSourceTerms = {}

        # Fixed Value Widgets
        self._turbulenceFixedValues = {}
        self._temperatureFixedValue = FixedValueWidget({"title": self.tr("Temperature"), "label": self.tr("Value (K)")})

        self._setup()
        self._connectSignalsSlots()

    def _setup(self):
        self._zoneTypeLayout.insertWidget(1, self._MRFZone)
        self._zoneTypeLayout.insertWidget(2, self._porousZone)
        self._zoneTypeLayout.insertWidget(3, self._slidingMeshZone)
        self._zoneTypeLayout.insertWidget(4, self._actuatorDiskZone)

        self._sourceTermsLayout.addWidget(self._massSourceTerm)
        self._sourceTermsLayout.addWidget(self._energySourceTerm)

        self._setupTurbulenceWidgets(["k", "epsilon"])
        self._setupMaterialWidgets(["O2"])

        self._fixedValuesLayout.addWidget(self._temperatureFixedValue)

        self._sourceTermsLayout.addStretch()
        self._fixedValuesLayout.addStretch()

    def _setupTurbulenceWidgets(self, turbulences):
        self._turbulenceTexts = {
            "k": {
                "title": self.tr("Turbulent Kinetic Energy, k"),
                "label": "k (㎡/s<sup>2</sup>)"
            },
            "epsilon": {
                "title": self.tr("Turbulent Dissipation Rate, ε)"),
                "label": "ε (㎡/s<sup>3</sup>)"
            },
            "omega": {
                "title": self.tr("Specific Dissipation Rate, ω"),
                "label": "ω (1/s)"
            },
            "nu": {
                "title": self.tr("Modified Turbulent Viscosity, ν"),
                "label": "ν (㎡/s)"
            },
        }

        for turbulence in turbulences:
            self._turbulenceSourceTerms[turbulence] = ConstantSourceWidget(self._turbulenceTexts[turbulence])
            self._sourceTermsLayout.addWidget(self._turbulenceSourceTerms[turbulence])
            self._turbulenceFixedValues[turbulence] = FixedValueWidget(self._turbulenceTexts[turbulence])
            self._fixedValuesLayout.addWidget(self._turbulenceFixedValues[turbulence])

    def _setupMaterialWidgets(self, materials):
        for material in materials:
            self._materialSourceTerms[material] = VariableSourceWidget(material)
            self._sourceTermsLayout.addWidget(self._materialSourceTerms[material])

    def _connectSignalsSlots(self):
        self._ui.none.toggled.connect(self._zoneTypeChanged)
        self._ui.MRF.toggled.connect(self._zoneTypeChanged)
        self._ui.porousZone.toggled.connect(self._zoneTypeChanged)
        self._ui.slidingMesh.toggled.connect(self._zoneTypeChanged)
        self._ui.actuatorDisk.toggled.connect(self._zoneTypeChanged)

    def _zoneTypeChanged(self, checked):
        if checked:
            self._MRFZone.setVisible(self._ui.MRF.isChecked())
            self._porousZone.setVisible(self._ui.porousZone.isChecked())
            self._slidingMeshZone.setVisible(self._ui.slidingMesh.isChecked())
            self._actuatorDiskZone.setVisible(self._ui.actuatorDisk.isChecked())