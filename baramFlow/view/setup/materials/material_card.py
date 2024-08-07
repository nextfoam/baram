#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB, Specification, Phase, MaterialType
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
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
        type_ = MaterialDB.getType(self._mid)
        specXPath = (MaterialDB.getXPath(db.getValue(self._xpath + '/specie/mixture'))
                     if type_ == MaterialType.SPECIE else self._xpath)

        specification = db.getValue(specXPath + '/density/specification')
        if specification == Specification.CONSTANT.value or not energyModelOn:
            self._ui.density.setText(db.getValue(self._xpath + '/density/constant') + ' kg/m<sup>3</sup>')
        else:
            self._ui.density.setText(MaterialDB.dbSpecificationToText(specification))

        viscositySpec = None
        if phase == Phase.SOLID or ModelsDB.getTurbulenceModel() == TurbulenceModel.INVISCID:
            self._ui.viscosistyWidget.hide()
        else:
            viscositySpec = db.getValue(specXPath + '/viscosity/specification')
            if viscositySpec == Specification.CONSTANT.value or not energyModelOn:
                self._ui.viscosity.setText(db.getValue(self._xpath + '/viscosity/constant') + ' kg/m·s')
            else:
                self._ui.viscosity.setText(MaterialDB.dbSpecificationToText(viscositySpec))

        if energyModelOn:
            self._ui.specificHeatWidget.show()
            specification = db.getValue(specXPath + '/specificHeat/specification')
            if specification == Specification.CONSTANT.value:
                self._ui.specificHeat.setText(db.getValue(self._xpath + '/specificHeat/constant') + ' J/kg·K')
            else:
                self._ui.specificHeat.setText(MaterialDB.dbSpecificationToText(specification))

            if viscositySpec != Specification.SUTHERLAND.value:
                self._ui.thermalConductivityWidget.show()
                specification = (db.getValue(self._xpath + '/thermalConductivity/specification')
                                 if type_ == MaterialType.NONMIXTURE else viscositySpec)
                if specification == Specification.CONSTANT.value:
                    self._ui.thermalConductivity.setText(
                        db.getValue(self._xpath + '/thermalConductivity/constant') + ' W/m·K')
                else:
                    self._ui.thermalConductivity.setText(MaterialDB.dbSpecificationToText(specification))
            else:
                self._ui.thermalConductivityWidget.hide()
        else:
            self._ui.specificHeatWidget.hide()
            self._ui.thermalConductivityWidget.hide()

    def _edit(self):
        self._dialog = MaterialDialog(self, self._mid)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def _remove(self):
        self.removeClicked.emit(self)

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._edit)
        self._ui.remove.clicked.connect(self._remove)
