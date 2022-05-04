#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from view.setup.materials.material_card_ui import Ui_MaterialCard
from .material import Material


class MaterialCard(QWidget):
    def __init__(self, parent, material):
        super().__init__()
        self._ui = Ui_MaterialCard()
        self._ui.setupUi(self)

        self._parent = parent
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
        if material.phase == Material.PHASE.Solid:
            self._ui.viscosistyWidget.setVisible(False)
        else:
            self._ui.viscosity.setText(material.viscosity + " kg/m·s")
        self._ui.thermalConductivity.setText(material.conductivity + " W/m·K")

    def _edit(self):
        self._parent.edit(self)

    def _remove(self):
        self._parent.remove(self)

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._edit)
        self._ui.remove.clicked.connect(self._remove)

