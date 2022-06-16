#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from coredb import coredb
from .material_db import MaterialDB, Specification, Phase
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

        self._db = coredb.CoreDB()
        self._xpath = MaterialDB.getXPath(mid)

        self._connectSignalsSlots()
        self._load()

    @property
    def name(self):
        return self._ui.name.text()

    def _load(self):
        self._ui.name.setText(self._db.getValue(self._xpath + '/name'))

        phase = MaterialDB.DBTextToPhase(self._db.getValue(self._xpath + '/phase'))
        self._ui.phase.setText("(" + MaterialDB.getPhaseText(phase) + ")")

        specification = self._db.getValue(self._xpath + '/density/specification')
        if specification == Specification.CONSTANT.value:
            self._ui.density.setText(self._db.getValue(self._xpath + '/density/constant') + ' kg/m<sup>3</sup>')
        else:
            self._ui.density.setText(MaterialDB.DBSpecificationToText(specification))

        specification = self._db.getValue(self._xpath + '/specificHeat/specification')
        if specification == Specification.CONSTANT.value:
            self._ui.specificHeat.setText(self._db.getValue(self._xpath + '/specificHeat/constant') + ' J/kg·K')
        else:
            self._ui.specificHeat.setText(MaterialDB.DBSpecificationToText(specification))

        if phase == Phase.SOLID:
            self._ui.viscosistyWidget.hide()
        else:
            specification = self._db.getValue(self._xpath + '/viscosity/specification')
            if specification == Specification.CONSTANT.value:
                self._ui.viscosity.setText(self._db.getValue(self._xpath + '/viscosity/constant') + ' kg/m·s')
            else:
                self._ui.viscosity.setText(MaterialDB.DBSpecificationToText(specification))

        specification = self._db.getValue(self._xpath + '/thermalConductivity/specification')
        if specification == Specification.CONSTANT.value:
            self._ui.thermalConductivity.setText(
                self._db.getValue(self._xpath + '/thermalConductivity/constant') + ' W/m·K')
        else:
            self._ui.thermalConductivity.setText(MaterialDB.DBSpecificationToText(specification))

    def _edit(self):
        if self._dialog is None:
            self._dialog = MaterialDialog(self, self._xpath)
            self._dialog.accepted.connect(self._load)

        self._dialog.open()

    def _remove(self):
        self.removeClicked.emit(self)

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._edit)
        self._ui.remove.clicked.connect(self._remove)
