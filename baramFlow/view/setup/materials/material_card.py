#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB, Specification, Phase
from baramFlow.coredb.models_db import ModelsDB
from .material_card_ui import Ui_MaterialCard
from .material_dialog import MaterialDialog


class MaterialCard(QWidget):
    removeClicked = Signal(QWidget)

    def __init__(self, mid):
        super().__init__()
        self._ui = Ui_MaterialCard()
        self._ui.setupUi(self)

        self._mid = mid
        self._dialog = None

        self._xpath = MaterialDB.getXPath(mid)

        self._connectSignalsSlots()
        self.load()

    @property
    def name(self):
        return self._ui.name.text()

    def load(self):
        db = coredb.CoreDB()

        self._ui.name.setText(db.getValue(self._xpath + '/name'))

        phase = MaterialDB.dbTextToPhase(db.getValue(self._xpath + '/phase'))
        self._ui.phase.setText("(" + MaterialDB.getPhaseText(phase) + ")")

        energyModelOn = ModelsDB.isEnergyModelOn()

        specification = db.getValue(self._xpath + '/density/specification')
        if specification == Specification.CONSTANT.value or not energyModelOn:
            self._ui.density.setText(db.getValue(self._xpath + '/density/constant') + ' kg/m<sup>3</sup>')
        else:
            self._ui.density.setText(MaterialDB.dbSpecificationToText(specification))

        if phase == Phase.SOLID:
            self._ui.viscosistyWidget.hide()
        else:
            specification = db.getValue(self._xpath + '/viscosity/specification')
            if specification == Specification.CONSTANT.value or not energyModelOn:
                self._ui.viscosity.setText(db.getValue(self._xpath + '/viscosity/constant') + ' kg/m·s')
            else:
                self._ui.viscosity.setText(MaterialDB.dbSpecificationToText(specification))

        if energyModelOn:
            self._ui.specificHeatWidget.show()
            specification = db.getValue(self._xpath + '/specificHeat/specification')
            if specification == Specification.CONSTANT.value:
                self._ui.specificHeat.setText(db.getValue(self._xpath + '/specificHeat/constant') + ' J/kg·K')
            else:
                self._ui.specificHeat.setText(MaterialDB.dbSpecificationToText(specification))

            self._ui.thermalConductivityWidget.show()
            specification = db.getValue(self._xpath + '/thermalConductivity/specification')
            if specification == Specification.CONSTANT.value:
                self._ui.thermalConductivity.setText(
                    db.getValue(self._xpath + '/thermalConductivity/constant') + ' W/m·K')
            else:
                self._ui.thermalConductivity.setText(MaterialDB.dbSpecificationToText(specification))
        else:
            self._ui.specificHeatWidget.hide()
            self._ui.thermalConductivityWidget.hide()

    def _edit(self):
        self._dialog = MaterialDialog(self, self._xpath)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def _remove(self):
        self.removeClicked.emit(self)

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._edit)
        self._ui.remove.clicked.connect(self._remove)
