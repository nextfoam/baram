#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from baramFlow.base.material.material import Phase, MaterialType, SpecificHeatSpecification, DensitySpecification, TransportSpecification
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.project import Project
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from .material_card_ui import Ui_MaterialCard
from .material_dialog import MaterialDialog


class MaterialCard(QWidget):
    removeClicked = Signal(QWidget)

    def __init__(self, mid: str):
        super().__init__()
        self._ui = Ui_MaterialCard()
        self._ui.setupUi(self)

        self._mid: str = mid
        self._dialog = None

        self._xpath = MaterialDB.getXPath(mid)

        self._connectSignalsSlots()
        self._updateEnabled()

    @property
    def type(self):
        return MaterialType.NONMIXTURE

    @property
    def mid(self) -> str:
        return self._mid

    @property
    def name(self):
        return self._ui.name.text()

    def load(self):
        db = coredb.CoreDB()

        self._ui.name.setText(MaterialDB.getName(self._mid))

        phase = MaterialDB.getPhase(self._mid)
        self._ui.phase.setText("(" + MaterialDB.getPhaseText(phase) + ")")

        energyModelOn = ModelsDB.isEnergyModelOn()

        densitySpec = DensitySpecification(db.getValue(self._xpath + '/density/specification'))
        if densitySpec == DensitySpecification.CONSTANT or not energyModelOn:
            self._ui.density.setText(db.getValue(self._xpath + '/density/constant') + ' kg/m<sup>3</sup>')
        else:
            self._ui.density.setText(MaterialDB.densitySpecToText(densitySpec))

        transportSpec = TransportSpecification(db.getValue(self._xpath + '/transport/specification'))
        if phase == Phase.SOLID or TurbulenceModelsDB.getModel() == TurbulenceModel.INVISCID:
            self._ui.viscosistyWidget.hide()
        else:
            self._ui.viscosistyWidget.show()
            if (MaterialDB.isNonNewtonianSpecification(transportSpec)
                    or (transportSpec != TransportSpecification.CONSTANT and energyModelOn)):
                self._ui.viscosity.setText(MaterialDB.transportSpecToText(transportSpec))
            else:
                self._ui.viscosity.setText(db.getValue(self._xpath + '/transport/viscosity') + ' kg/m·s')

        if energyModelOn:
            self._ui.specificHeatWidget.show()
            specificHeatSpec = SpecificHeatSpecification(db.getValue(self._xpath + '/specificHeat/specification'))
            if specificHeatSpec == SpecificHeatSpecification.CONSTANT:
                self._ui.specificHeat.setText(db.getValue(self._xpath + '/specificHeat/constant') + ' J/kg·K')
            else:
                self._ui.specificHeat.setText(MaterialDB.specificHeatSpecToText(specificHeatSpec))

            if phase != Phase.SOLID \
                    and (TurbulenceModelsDB.getModel() == TurbulenceModel.INVISCID
                         or transportSpec == TransportSpecification.SUTHERLAND):
                self._ui.thermalConductivityWidget.hide()
            else:
                self._ui.thermalConductivityWidget.show()
                if transportSpec == TransportSpecification.CONSTANT:
                    self._ui.thermalConductivity.setText(
                        db.getValue(self._xpath + '/transport/thermalConductivity') + ' W/m·K')
                else:
                    self._ui.thermalConductivity.setText(MaterialDB.transportSpecToText(transportSpec))
        else:
            self._ui.specificHeatWidget.hide()
            self._ui.thermalConductivityWidget.hide()

    def _connectSignalsSlots(self):
        Project.instance().solverStatusChanged.connect(self._updateEnabled)

        self._ui.edit.clicked.connect(self._edit)
        self._ui.remove.clicked.connect(self._remove)

    def _updateEnabled(self):
        caseManager = CaseManager()
        self._ui.edit.setEnabled(not caseManager.isActive())
        self._ui.remove.setEnabled(not caseManager.isActive())

    def _edit(self):
        self._dialog = MaterialDialog(self, self._mid)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def _remove(self):
        self.removeClicked.emit(self)
