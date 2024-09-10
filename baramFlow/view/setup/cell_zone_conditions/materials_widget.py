#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit
from PySide6.QtCore import Signal

from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import Phase
from .cavitation_widget import CavitationWidget
from .materials_widget_ui import Ui_MaterialsWidget
from .material_selector_dialog import MaterialSectorDialog


class SurfaceTensionRow:
    def __init__(self, parent, material1, material2, value):
        self._label1 = QLabel(material1, parent)
        self._label2 = QLabel('- ' + material2, parent)
        self._valueEdit = QLineEdit(parent)

        layout = parent.layout()
        row = layout.rowCount()
        layout.addWidget(self._label1, row, 0)
        layout.addWidget(self._label2, row, 1)
        layout.addWidget(self._valueEdit, row, 2)

        self._valueEdit.setText(value)
        self._valueEdit.setFixedWidth(60)

    def value(self):
        return self._valueEdit.text()


class SurfaceTensionWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setColumnMinimumWidth(0, 50)
        layout.setColumnMinimumWidth(1, 120)
        layout.setColumnMinimumWidth(2, 60)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)

        self._rows = {}

    def addRow(self, key, material1, material2, value):
        self._rows[key] = SurfaceTensionRow(self, material1, material2, value)

    def rows(self):
        return [[key[0], key[1], self._rows[key]] for key in self._rows]

    def values(self):
        return [[key[0], key[1], self._rows[key].value()] for key in self._rows]


class MaterialsWidget(QWidget):
    materialsChanged = Signal(str, list)

    def __init__(self, rname):
        super().__init__()
        self._ui = Ui_MaterialsWidget()
        self._ui.setupUi(self)

        self._rname = rname
        self._db = coredb.CoreDB()
        self._xpath = RegionDB.getXPath(self._rname)

        self._materialsMap = {}
        self._surfaceTensionsMap = {}

        self._material = None
        self._secondaryMaterials = None

        self._surfaceTensionWidget = None
        self._cavitationWidget = CavitationWidget(self, self._ui, self._xpath)

        self._dialog = None

        if ModelsDB.isMultiphaseModelOn():
            self._ui.singlephase.hide()

            layout = QVBoxLayout(self._ui.surfaceTension)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            self._ui.multiphase.hide()

            materials = (MaterialDB.getMaterials() if ModelsDB.isSpeciesModelOn()
                         else MaterialDB.getMaterials('nonmixture'))
            for mid, name, _, _ in materials:
                self._ui.material.addItem(name, mid)

        self._connectSignalsSlots()

    def load(self):
        db = coredb.CoreDB()
        self._material = db.getValue(self._xpath + '/material')

        if ModelsDB.isMultiphaseModelOn():
            surfaceTensions = db.getSurfaceTensions(self._rname)
            for mid1, mid2, value in surfaceTensions:
                self._addSurfaceTensionToMap(mid1, mid2, value)

            self._ui.primaryMaterial.setText(self._addMaterialToMap(self._material))
            self._setSecondaryMaterials(RegionDB.getSecondaryMaterials(self._rname))
            self._cavitationWidget.load()
        else:
            self._ui.material.setCurrentText(MaterialDB.getName(self._material))

    def updateDB(self, db):
        if ModelsDB.isMultiphaseModelOn():
            if self._surfaceTensionWidget:
                sfXpath = self._xpath + '/phaseInteractions/surfaceTensions'
                if surfaceTensions := self._surfaceTensionWidget.values():
                    for mid1, mid2, value in surfaceTensions:
                        db.addElementFromString(sfXpath, '<surfaceTension xmlns="http://www.baramcfd.org/baram">'
                                                         f' <mid>{mid1}</mid><mid>{mid2}</mid><value>0</value>'
                                                         '</surfaceTension>')
                        db.setValue(f'{sfXpath}/surfaceTension[mid="{mid1}"][mid="{mid2}"]/value', value,
                                    self.tr('Surface Tension'))

            self._cavitationWidget.updateDB(db)

        return True

    def _connectSignalsSlots(self):
        self._ui.material.currentTextChanged.connect(self._materialChanged)
        self._ui.materialsSelect.clicked.connect(self._selectMaterials)

    def _addMaterialToMap(self, mid):
        name = MaterialDB.getName(mid)
        self._materialsMap[mid] = name
        return name

    def _addSurfaceTensionToMap(self, mid1: str, mid2: str, value):
        self._surfaceTensionsMap[(mid1, mid2)] = value
        self._surfaceTensionsMap[(mid2, mid1)] = value

    def _setMaterial(self, mid: str):
        self._material = mid
        self._ui.primaryMaterial.setText(self._addMaterialToMap(self._material))

    def _setSecondaryMaterials(self, materials):
        self._secondaryMaterials = materials

        self._ui.secondaryMaterials.clear()
        if self._surfaceTensionWidget:
            item = self._ui.surfaceTension.layout().takeAt(0)
            item.widget().deleteLater()

        self._surfaceTensionWidget = SurfaceTensionWidget(self)
        self._ui.surfaceTension.layout().addWidget(self._surfaceTensionWidget)

        for mid in materials:
            self._ui.secondaryMaterials.addItem(self._addMaterialToMap(mid))

        self._addSurfaceTensionRows(self._material, 0)
        for i in range(len(self._secondaryMaterials)):
            self._addSurfaceTensionRows(self._secondaryMaterials[i], i + 1)

        self._cavitationWidget.setEnabled(len(materials) == 1
                                          and MaterialDB.getPhase(self._material) == Phase.GAS
                                          and MaterialDB.getPhase(materials[0]) == Phase.LIQUID)

    def _materialChanged(self):
        self._material = self._ui.material.currentData()
        self.materialsChanged.emit(self._material, [])

    def _selectMaterials(self):
        if self._surfaceTensionWidget:
            for mid1, mid2, row in self._surfaceTensionWidget.rows():
                self._addSurfaceTensionToMap(mid1, mid2, row.value())

        self._dialog = MaterialSectorDialog(
            self, self._material, self._secondaryMaterials, self._cavitationWidget.isChecked())
        self._dialog.open()
        self._dialog.accepted.connect(self._materialsSelected)

    def _materialsSelected(self):
        secondaryMaterials = self._dialog.getSecondaries()
        self._setMaterial(self._dialog.getPrimaryMaterial())
        self._setSecondaryMaterials(secondaryMaterials)
        self.materialsChanged.emit(self._material, secondaryMaterials)

    def _addSurfaceTensionRows(self, mid: str, offset):
        for i in range(offset, len(self._secondaryMaterials)):
            key = (mid, self._secondaryMaterials[i])
            self._surfaceTensionWidget.addRow(
                key, self._materialsMap[mid], self._materialsMap[self._secondaryMaterials[i]],
                self._surfaceTensionsMap[key] if key in self._surfaceTensionsMap else '0')
