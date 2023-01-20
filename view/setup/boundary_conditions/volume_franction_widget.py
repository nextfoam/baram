#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit

from coredb import coredb
from coredb.models_db import ModelsDB
from coredb.region_db import RegionDB
from coredb.boundary_db import BoundaryDB
from coredb.material_db import MaterialDB


class FractionRow:
    def __init__(self, layout, mid):
        self._label = MaterialDB.getName(mid)
        self._value = QLineEdit('0')
        layout.addRow(self._label, self._value)

    @property
    def label(self):
        return self._label

    @property
    def value(self):
        return self._value.text()

    @value.setter
    def value(self, value):
        self._value.setText(value)


class VolumeFractionWidget(QWidget):
    def __init__(self, bcid):
        super().__init__()

        self._on = ModelsDB.isMultiphaseModelOn() or ModelsDB.isSpeciesModelOn()
        self._fractions = {}

        self._db = coredb.CoreDB()
        self._xpath = BoundaryDB.getXPath(bcid)

        if self._on:
            layout = QVBoxLayout(self)
            groupBox = QGroupBox(self.tr('Volume Fraction'))
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(groupBox)

            layout = QFormLayout(groupBox)
            for mid in RegionDB.getSecondaryMaterials(BoundaryDB.getBoundaryRegion(bcid)):
                self._fractions[mid] = FractionRow(layout, mid)

    def on(self):
        return self._on

    def load(self):
        if self._on:
            xpath = self._xpath + '/volumeFractions/volumeFraction'
            materials = self._db.getList(xpath, 'material')
            for mid in materials:
                self._fractions[mid].value = self._db.getValue(f'{xpath}[material="{mid}"]/fraction')

    def appendToWriter(self, writer):
        if self._on:
            writer.clearElement(self._xpath + '/volumeFractions')
            for mid in self._fractions:
                writer.addElement(self._xpath + '/volumeFractions',
                                  BoundaryDB.buildVolumeFractionElement(mid, self._fractions[mid].value),
                                  self._fractions[mid].label)
