#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QGroupBox, QFormLayout, QLineEdit

from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.coredb_writer import CoreDBWriter


MIN_FRACTION = 0.0
MAX_FRACTION = 1.0
DECIMAL_PRECISION = 1000  # Default value for QDoubleValidator


class FractionRow:

    def __init__(self, layout, mid):
        self._label = MaterialDB.getName(mid)
        self._value = QLineEdit('0')
        self._value.setValidator(QDoubleValidator(MIN_FRACTION, MAX_FRACTION, DECIMAL_PRECISION))
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
    def __init__(self, rname):
        super().__init__(self.tr('Volume Fraction'))

        self._on = ModelsDB.isMultiphaseModelOn()
        self._fractions = {}

        self._rname = rname

        self._volumeFractionsLayout = None

        if self._on:
            self._volumeFractionsLayout = QFormLayout(self)
            for mid in RegionDB.getSecondaryMaterials(rname):
                self._fractions[mid] = FractionRow(self._volumeFractionsLayout, mid)

    def on(self):
        return self._on

    def load(self, xpath):
        if self._on:
            for mid in RegionDB.getSecondaryMaterials(self._rname):
                if mid not in self._fractions:
                    self._fractions[mid] = FractionRow(self._volumeFractionsLayout, mid)

                try:
                    db = coredb.CoreDB()
                    value = db.getValue(f'{xpath}/volumeFraction[material="{mid}"]/fraction')
                except LookupError:
                    value = '0'

                self._fractions[mid].value = value

    def validate(self) -> (bool, str):
        if self._on:
            sumFraction = 0.0  # Sum of secondary material fractions
            for mid in self._fractions:
                value = float(self._fractions[mid].value)
                if value < MIN_FRACTION:
                    return False, self.tr('Fraction should have positive value')
                if value > MAX_FRACTION:
                    return False, self.tr(f'Fraction should be less than or equal to 1.0')
                sumFraction += value

            if sumFraction > MAX_FRACTION:
                return False, self.tr('Sum of fractions should be less than or equal to 1.0')

        return True, ''

    async def appendToWriter(self, writer: CoreDBWriter, xpath):
        if self._on:
            for mid in self._fractions:
                inputValue = self._fractions[mid].value
                fractionPath = xpath + f'/volumeFraction/[material="{mid}"]/fraction'

                try:
                    db = coredb.CoreDB()
                    savedValue = db.getValue(fractionPath)
                except LookupError:  # the material should be added if it is not there
                    writer.addElement(xpath,
                                        f'''
                                            <volumeFraction xmlns="http://www.baramcfd.org/baram">
                                                <material>{mid}</material>
                                                <fraction>{inputValue}</fraction>
                                            </volumeFraction>
                                        ''',
                                      self._fractions[mid].label)
                else:
                    if inputValue != savedValue:
                        writer.append(fractionPath, inputValue, self._fractions[mid].label)

        return True
