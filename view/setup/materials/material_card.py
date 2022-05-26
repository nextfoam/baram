#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from .material_card_ui import Ui_MaterialCard
from .material import Phase
from .material_db import MaterialDB
from .material_dialog import MaterialDialog


class MaterialCard(QWidget):
    removeClicked = Signal(QWidget)

    def __init__(self, parent, material):
        super().__init__()
        self._ui = Ui_MaterialCard()
        self._ui.setupUi(self)

        self._parent = parent
        self._dialog = None
        self.setMaterial(material)

        self._connectSignalsSlots()

    @property
    def name(self):
        return self._ui.name.text()

    def setMaterial(self, material):
        self._ui.name.setText(material.name)
        self._ui.phase.setText("(" + material.phase.name + ")")
        self._ui.density.setText(material.density + " kg/㎥")
        self._ui.specificHeat.setText(material.specificHeat + " J/kg·K")
        if material.phase == Phase.SOLID:
            self._ui.viscosistyWidget.hide()
        else:
            self._ui.viscosity.setText(material.viscosity + " kg/m·s")
        self._ui.thermalConductivity.setText(material.conductivity + " W/m·K")

    def _edit(self):
        if self._dialog is None:
            self._dialog = MaterialDialog(MaterialDB.instance().getMaterial(self._ui.name.text()))

        self._dialog.open()

    def _remove(self):
        self.removeClicked.emit(self)

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._edit)
        self._ui.remove.clicked.connect(self._remove)

