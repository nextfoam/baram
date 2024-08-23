#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QGroupBox, QFormLayout, QLineEdit

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import boolToDBText
from baramFlow.coredb.material_db import MaterialDB, MaterialType
from widgets.async_message_box import AsyncMessageBox


class SpeciesWidget(QGroupBox):
    def __init__(self, mid, species=None, optional=False):
        super().__init__()

        self._mid = mid

        self._on = False
        self._layout = None
        self._species = {}
        self._optional = optional

        self.setTitle(MaterialDB.getName(self._mid))
        self.setCheckable(self._optional)
        self.setChecked(False)

        if MaterialDB.getType(self._mid) == MaterialType.MIXTURE:
            self._on = True
            self._layout = QFormLayout(self)
            for mid, name in species or MaterialDB.getSpecies(mid).items():
                editor = QLineEdit()
                self._layout.addRow(name, editor)
                self._species[mid] = (name, editor)

    def mid(self):
        return self._mid

    def species(self):
        return self._species.keys()

    def on(self):
        return self._on

    def load(self, speciesXPath):
        if self._on:
            db = coredb.CoreDB()
            xpath = f'{speciesXPath}/mixture[mid="{self._mid}"]'
            if db.exists(xpath):
                if self._optional:
                    self.setChecked(db.getAttribute(xpath, 'disabled') == 'false')

                for mid in self._species:
                    _, editor = self._species[mid]
                    editor.setText(db.getValue(f'{xpath}/specie[mid="{mid}"]/value'))
            else:
                self.setChecked(False)
                for mid in self._species:
                    _, editor = self._species[mid]
                    editor.setText('0')

    async def appendToWriter(self, writer, speciesXPath):
        if self._on:
            xpath = f'{speciesXPath}/mixture[mid="{self._mid}"]'
            if self._optional:
                writer.setAttribute(xpath, 'disabled', boolToDBText(not self.isChecked()))
                if not self.isChecked():
                    return True

            totalRatio = 0
            for mid, row in self._species.items():
                try:
                    fieldName, editor = row
                    writer.append(f'{xpath}/specie[mid="{mid}"]/value',
                                  editor.text(), fieldName)
                    totalRatio += float(editor.text())
                except ValueError:
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'), self.tr('{} must be a float').format(row[0]))
                    return False

            if totalRatio == 0:
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'),
                    self.tr('The sum of the composition ratios of the mixture "{}" is 0.').format(
                        MaterialDB.getName(self._mid)))
                return False

        return True
