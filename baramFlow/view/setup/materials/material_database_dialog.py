#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import qasync
from PySide6.QtWidgets import QDialog, QTreeWidgetItem, QFileDialog

from libbaram.validation import TextType, EnumType, FloatType, validateData, ValidationError
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb.app_settings import AppSettings
from baramFlow.coredb.material_schema import Phase
from baramFlow.coredb.materials_base import MaterialsBase
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

        self._materials = dict(MaterialsBase.getMaterials())

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

        values = self._materials[next(iter(self._materials))]
        columns = list(values.keys())
        columns.insert(0, self.tr('Name'))

        self._ui.list.setColumnCount(len(columns))
        self._ui.list.setHeaderLabels(columns)

        for name, values in self._materials.items():
            QTreeWidgetItem(self._ui.list, [name, *values.values()])

    def _deleteMaterials(self):
        for item in self._ui.list.selectedItems():
            name = item.text(0)
            del self._materials[name]
            self._ui.list.invisibleRootItem().removeChild(item)

    def _selectionChanged(self):
        selected = len(self._ui.list.selectedItems())
        self._ui.delete_.setEnabled(0 < selected < self._ui.list.topLevelItemCount())

    def _openExportDialog(self):
        self._dialog = QFileDialog(self, self.tr('Export Materials'), '', self.tr('CSV (*.csv)'))
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.fileSelected.connect(self._exportDatabase)
        self._dialog.open()

    def _openImportDialog(self):
        self._dialog = MaterialsImportDialog(self)
        self._dialog.accepted.connect(self._importDatabase)
        self._dialog.open()

    def _accept(self):
        AppSettings.updateMaterialsDB(self._materials)
        self.accept()

    def _exportDatabase(self, file):
        df = pd.DataFrame.from_dict(self._materials, orient='index')
        df.to_csv(file, index_label='name')

    @qasync.asyncSlot()
    async def _importDatabase(self):
        df = pd.read_csv(self._dialog.selectedFile(), header=0, index_col=0, dtype=str)
        if list(df.columns) != material_columns:
            await AsyncMessageBox().information(
                self, self.tr('Import Error'), self.tr('The file has incorrect columns.'))

            return

        df = df.transpose()
        duplicated = df.columns[df.columns.duplicated()]
        if not duplicated.empty:
            await AsyncMessageBox().information(
                self, self.tr('Import Error'), self.tr('Duplicate keys detected: {}'.format('", "'.join(duplicated))))

            return

        rawData = df.where(pd.notnull(df), None).to_dict()
        materials = {}

        name = None
        try:
            for key, data in rawData.items():
                name = key.strip()
                if name in materials:
                    await AsyncMessageBox().information(
                        self, self.tr('Import Error'), self.tr('Duplicated Material Name - {}'.format(name)))
                    return

                phase = data['phase']
                if phase not in schema:
                    await AsyncMessageBox().information(
                        self, self.tr('Import Error'),
                        self.tr('Phase of Material "{}" is invalid phase.<br/>Available phases - {}').format(
                            name, ', '.join(schema.keys())))
                    return

                materials[name] = validateData(data, schema[data['phase'].strip()])
        except ValidationError as e:
            await AsyncMessageBox().information(
                self, self.tr('Import Error'),
                self.tr('Column "{0}" of Material "{1}" - {2}'.format(e.name, name, e.message)))

        if self._dialog.isClearChecked():
            self._materials = materials
        else:
            self._materials.update(materials)

        self._updateList()
