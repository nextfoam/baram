#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QCheckBox, QLabel, QLineEdit
from PySide6.QtCore import Signal

from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.material_db import MaterialDB
from .materials_widget_ui import Ui_MaterialsWidget
from .material_selector_dialog import MaterialSectorDialog


class SurfaceTensionRow:
    def __init__(self, parent, material1, material2, value):
        self._checkBox = QCheckBox(parent)
        self._label1 = QLabel(material1, parent)
        self._label2 = QLabel('- ' + material2, parent)
        self._valueEdit = QLineEdit(parent)

        layout = parent.layout()
        row = layout.rowCount()
        layout.addWidget(self._checkBox, row, 0)
        layout.addWidget(self._label1, row, 1)
        layout.addWidget(self._label2, row, 2)
        layout.addWidget(self._valueEdit, row, 3)

        if value is None:
            value = '0'
            self._checkBox.setChecked(False)
        else:
            self._checkBox.setChecked(True)

        self._valueEdit.setText(value)
        self._valueEdit.setEnabled(self._checkBox.isChecked())

        self._checkBox.stateChanged.connect(self._checkBoxClicked)
        self._valueEdit.setFixedWidth(60)

    def isChecked(self):
        return self._checkBox.isChecked()

    def value(self):
        return self._valueEdit.text()

    def _checkBoxClicked(self):
        self._valueEdit.setEnabled(self._checkBox.isChecked())


class SurfaceTensionWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setColumnMinimumWidth(0, 10)
        layout.setColumnMinimumWidth(1, 50)
        layout.setColumnMinimumWidth(2, 120)
        layout.setColumnMinimumWidth(3, 60)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 1)

        self._rows = {}

    def addRow(self, key, material1, material2, value):
        self._rows[key] = SurfaceTensionRow(self, material1, material2, value)

    def rows(self):
        return [[key[0], key[1], self._rows[key]] for key in self._rows]

    def values(self):
        return [[key[0], key[1], self._rows[key].value()] for key in self._rows if self._rows[key].isChecked()]


class MaterialsWidget(QWidget):
    materialsChanged = Signal(str, list)

    def __init__(self, rname, multiphase):
        super().__init__()
        self._ui = Ui_MaterialsWidget()
        self._ui.setupUi(self)

        self._rname = rname
        self._multiphase = multiphase
        self._xpath = RegionDB.getXPath(self._rname)

        self._materialsMap = {}
        self._surfaceTensionsMap = {}

        self._material = None
        self._secondaryMaterials = None

        self._surfaceTensionWidget = None
        self._dialog = None

        if multiphase:
            self._ui.singlephase.setVisible(False)

            layout = QVBoxLayout(self._ui.surfaceTension)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            self._ui.multiphase.setVisible(False)

            db = coredb.CoreDB()
            materials = db.getMaterials() if ModelsDB.isSpeciesModelOn() else db.getMaterials('nonmixture')
            for mid, name, _, _ in materials:
                self._ui.material.addItem(name, str(mid))

        self._connectSignalsSlots()

    def load(self):
        db = coredb.CoreDB()
        self._material = db.getValue(self._xpath + '/material')

        if self._multiphase:
            surfaceTensions = db.getSurfaceTensions(self._rname)
            for mid1, mid2, value in surfaceTensions:
                self._addSurfaceTensionToMap(mid1, mid2, value)

            self._ui.primaryMaterial.setText(self._addMaterialToMap(self._material))
            if MaterialDB.isFluid(self._material):
                self._setSecondaryMaterials(RegionDB.getSecondaryMaterials(self._rname))
        else:
            self._ui.material.setCurrentText(MaterialDB.getName(self._material))

    def updateDB(self, newDB):
        if self._surfaceTensionWidget:
            sfXpath = self._xpath + '/phaseInteractions/surfaceTensions'
            if surfaceTensions := self._surfaceTensionWidget.values():
                for mid1, mid2, value in surfaceTensions:
                    newDB.addElementFromString(sfXpath, '<surfaceTension xmlns="http://www.baramcfd.org/baram">'
                                                     f' <mid>{mid1}</mid><mid>{mid2}</mid><value>0</value>'
                                                     '</surfaceTension>')
                    newDB.setValue(f'{sfXpath}/surfaceTension[mid="{mid1}"][mid="{mid2}"]/value', value,
                                self.tr('Surface Tension'))

        return True

    def _connectSignalsSlots(self):
        self._ui.material.currentTextChanged.connect(self._materialChanged)
        self._ui.materialsSelect.clicked.connect(self._selectMaterials)

    def _addMaterialToMap(self, mid):
        name = MaterialDB.getName(mid)
        self._materialsMap[mid] = name
        return name

    def _addSurfaceTensionToMap(self, mid1, mid2, value):
        self._surfaceTensionsMap[(mid1, mid2)] = value
        self._surfaceTensionsMap[(mid2, mid1)] = value

    def _setMaterial(self, mid):
        self._material = mid
        self._ui.primaryMaterial.setText(self._addMaterialToMap(self._material))

    def _setSecondaryMaterials(self, materials, default=None):
        self._secondaryMaterials = materials

        self._ui.secondaryMaterials.clear()
        if self._surfaceTensionWidget:
            item = self._ui.surfaceTension.layout().takeAt(0)
            item.widget().deleteLater()

        if not materials:
            self._ui.fluid.setVisible(False)
            self._surfaceTensionWidget = None
            return

        self._ui.fluid.setVisible(True)
        self._surfaceTensionWidget = SurfaceTensionWidget(self)
        self._ui.surfaceTension.layout().addWidget(self._surfaceTensionWidget)

        for mid in materials:
            self._ui.secondaryMaterials.addItem(self._addMaterialToMap(mid))

        self._addSurfaceTensionRows(self._material, 0, default)
        for i in range(len(self._secondaryMaterials)):
            self._addSurfaceTensionRows(self._secondaryMaterials[i], i + 1, default)

    def _materialChanged(self):
        self._material = self._ui.material.currentData()
        self.materialsChanged.emit(self._material, [])

    def _selectMaterials(self):
        if self._surfaceTensionWidget:
            for mid1, mid2, row in self._surfaceTensionWidget.rows():
                self._addSurfaceTensionToMap(mid1, mid2, row.value() if row.isChecked() else None)

        self._dialog = MaterialSectorDialog(self, self._material, self._secondaryMaterials)
        self._dialog.open()
        self._dialog.accepted.connect(self._materialsSelected)

    def _materialsSelected(self):
        secondaryMaterials = self._dialog.getSecondaries()
        self._setMaterial(self._dialog.getPrimaryMaterial())
        self._setSecondaryMaterials(secondaryMaterials)
        self.materialsChanged.emit(self._material, secondaryMaterials)

    def _addSurfaceTensionRows(self, mid, offset, default):
        for i in range(offset, len(self._secondaryMaterials)):
            key = (str(mid), self._secondaryMaterials[i])
            self._surfaceTensionWidget.addRow(
                key, self._materialsMap[mid], self._materialsMap[self._secondaryMaterials[i]],
                self._surfaceTensionsMap[key] if key in self._surfaceTensionsMap else default)
