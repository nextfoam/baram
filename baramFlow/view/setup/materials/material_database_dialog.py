#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTreeWidgetItem, QFileDialog, QHeaderView

from libbaram.simple_db.simple_schema import TextType, EnumType, FloatType, ValidationError
from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.material.database import materialsBase, liquidSchema, gasSchema, solidSchema
from baramFlow.base.material.database import loadDatabase, saveDatabase
from baramFlow.base.material.material import Phase
from .material_database_dialog_ui import Ui_MaterialDatabaseDialog
from .materials_import_dialog import MaterialsImportDialog


def baseSchema(optionalColmuns):
    schema = {
        'CoolPropName': TextType().setOptional(),
        'chemicalFormula': TextType().setOptional(),
        'phase': EnumType(Phase),
        'molecularWeight': FloatType(),
        'density': FloatType(),
        'viscosity': FloatType(),
        'thermalConductivity': FloatType(),
        'specificHeat': FloatType(),
        'emissivity': FloatType(),
        'absorptionCoefficient': FloatType(),
        'sutherlandTemperature': FloatType(),
        'sutherlandCoefficient': FloatType(),
        'surfaceTension': FloatType(),
        'saturationPressure': FloatType(),
        'criticalTemperature': FloatType(),
        'criticalPressure': FloatType(),
        'criticalDensity': FloatType(),
        'acentricFactor':FloatType()
    }

    for column in optionalColmuns:
        schema[column].setOptional()

    return schema


schema = {
    Phase.GAS.value: baseSchema(['emissivity', 'surfaceTension', 'saturationPressure']),
    Phase.LIQUID.value: baseSchema([
        'emissivity', 'absorptionCoefficient', 'sutherlandTemperature', 'sutherlandCoefficient',
        'criticalTemperature', 'criticalPressure', 'criticalDensity', 'acentricFactor']),
    Phase.SOLID.value: baseSchema([
        'molecularWeight', 'viscosity', 'absorptionCoefficient', 'sutherlandTemperature', 'sutherlandCoefficient',
        'surfaceTension', 'saturationPressure',
        'criticalTemperature', 'criticalPressure', 'criticalDensity', 'acentricFactor']),
}


material_columns = list(schema[Phase.GAS.value].keys())


class MaterialDatabaseDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MaterialDatabaseDialog()
        self._ui.setupUi(self)

        self._columns = None
        self._materials = materialsBase.getRawData()

        columns = dict.fromkeys(liquidSchema)
        columns.update(dict.fromkeys(gasSchema))
        columns.update(dict.fromkeys(solidSchema))
        self._columns = list(columns.keys())

        self._ui.list.setColumnCount(len(self._columns))
        self._ui.list.setHeaderLabels(self._columns)
        self._ui.list.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self._connectSignalsSlots()
        self._updateList()

    def _connectSignalsSlots(self):
        self._ui.list.itemSelectionChanged.connect(self._selectionChanged)
        self._ui.delete_.clicked.connect(self._deleteMaterials)
        self._ui.export_.clicked.connect(self._openExportDialog)
        self._ui.import_.clicked.connect(self._openImportDialog)
        self._ui.ok.clicked.connect(self._accept)

    def _updateList(self):
        self._ui.list.clear()

        phases = ['liquid', 'gas', 'solid']

        for key, data in self._materials.items():
            item = QTreeWidgetItem(self._ui.list, [data['name']])
            for phase in phases:
                if material := data.get(phase):
                    values = [str(material.get(column, '')) for column in self._columns]
                    values[0] = f'{values[0]} ({phase})'
                    materialItem = QTreeWidgetItem(item, values)
                    materialItem.setData(0, Qt.ItemDataRole.UserRole, phase)

        self._ui.list.expandAll()

    def _deleteMaterials(self):
        for item in self._ui.list.selectedItems():
            if parent := item.parent():
                parentName = parent.text(0)
                if parentName in self._materials:
                    self._materials[parentName].pop(item.data(0, Qt.ItemDataRole.UserRole))
                parent.removeChild(item)
                topLevelItem = None if parent.childCount() > 0 else parent
            else:
                topLevelItem = item

            if topLevelItem:
                self._materials.pop(topLevelItem.text(0), None)
                self._ui.list.invisibleRootItem().removeChild(topLevelItem)

    def _selectionChanged(self):
        selected = len(self._ui.list.selectedItems())
        self._ui.delete_.setEnabled(0 < selected < self._ui.list.topLevelItemCount())

    def _openExportDialog(self):
        self._dialog = QFileDialog(self, self.tr('Export Materials'), '', self.tr('YAML (*.yaml)'))
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.fileSelected.connect(self._exportDatabase)
        self._dialog.open()

    def _openImportDialog(self):
        self._dialog = MaterialsImportDialog(self)
        self._dialog.accepted.connect(self._importDatabase)
        self._dialog.open()

    def _accept(self):
        materialsBase.update(self._materials)
        self.accept()

    def _exportDatabase(self, path):
        saveDatabase(path, self._materials)

    @qasync.asyncSlot()
    async def _importDatabase(self):
        try:
            loaded = loadDatabase(self._dialog.selectedFile())
        except ValidationError as e:
            AsyncMessageBox().information(self, self.tr('Input Error'), e.toMessage())
            return

        if self._dialog.isClearChecked():
            self._materials = loaded
        else:
            self._materials.update(loaded)

        self._updateList()
