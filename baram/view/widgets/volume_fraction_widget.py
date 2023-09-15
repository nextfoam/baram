#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QGroupBox, QFormLayout, QLineEdit, QMessageBox

from baram.coredb import coredb
from baram.coredb.models_db import ModelsDB
from baram.coredb.region_db import RegionDB
from baram.coredb.boundary_db import BoundaryDB
from baram.coredb.material_db import MaterialDB
from baram.coredb.coredb_writer import CoreDBWriter


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


class VolumeFractionWidget(QGroupBox):
    def __init__(self, rname, xpath):
        super().__init__(self.tr('Volume Fraction'))

        self._on = ModelsDB.isMultiphaseModelOn() or ModelsDB.isSpeciesModelOn()
        self._fractions = {}

        self._db = coredb.CoreDB()
        self._rname = rname
        self._xpath = xpath

        self._volumeFractionsLayout = None

        if self._on:
            self._volumeFractionsLayout = QFormLayout(self)
            for mid in RegionDB.getSecondaryMaterials(rname):
                self._fractions[mid] = FractionRow(self._volumeFractionsLayout, mid)

    def on(self):
        return self._on

    def load(self):
        if self._on:
            xpath = self._xpath + '/volumeFractions/volumeFraction'

            for mid in RegionDB.getSecondaryMaterials(self._rname):
                if mid not in self._fractions:
                    self._fractions[mid] = FractionRow(self._volumeFractionsLayout, mid)

                try:
                    value = self._db.getValue(f'{xpath}[material="{mid}"]/fraction')
                except LookupError:
                    value = '0'

                self._fractions[mid].value = value

    def appendToWriter(self, writer: CoreDBWriter):
        if self._on:
            for mid in self._fractions:
                try:
                    decimal = float(self._fractions[mid].value)
                except ValueError:
                    QMessageBox.critical(self, self.tr("Input Error"),
                                         self.tr(f'{self._fractions[mid].label} must be a float.'))
                    return False

            for mid in self._fractions:
                inputValue = self._fractions[mid].value
                fractionPath = self._xpath + f'/volumeFractions/volumeFraction/[material="{mid}"]/fraction'
                try:
                    savedValue = self._db.getValue(fractionPath)
                except LookupError:  # the material should be added if it is not there
                    writer.addElement(self._xpath + '/volumeFractions',
                                      BoundaryDB.buildVolumeFractionElement(mid, inputValue), self._fractions[mid].label)
                else:
                    if inputValue != savedValue:
                        writer.append(fractionPath, inputValue, self._fractions[mid].label)

        return True
