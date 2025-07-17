#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog, QListWidgetItem

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import Phase, MaterialType
from baramFlow.coredb.materials_base import MaterialsBase
from baramFlow.coredb.models_db import ModelsDB
from widgets.async_message_box import AsyncMessageBox
from .material_add_dialog_ui import Ui_MaterialAddDialog
from .material_database_dialog import MaterialDatabaseDialog


class MaterialItem(QListWidgetItem):
    def __init__(self, listWidget, name: str, phase):
        super().__init__(f'{name} ({MaterialDB.getPhaseText(phase)})', listWidget)

        self._name = name
        self._textForFilter = name.lower()
        self._phase = phase

    def name(self):
        return self._name

    def phase(self):
        return self._phase

    def filter(self, text):
        self.setHidden(text not in self._textForFilter and not self.isSelected())


class MaterialAddDialog(QDialog):
    def __init__(self, parent, mixture=None):
        super().__init__(parent)
        self._ui = Ui_MaterialAddDialog()
        self._ui.setupUi(self)

        self._type = MaterialType.NONMIXTURE if mixture is None else MaterialType.SPECIE
        self._mixture = mixture
        self._added = None

        self._ui.createMixture.setVisible(ModelsDB.isSpeciesModelOn() and self._type != MaterialType.SPECIE)

        self._connectSignalsSlots()
        self._load()

    def result(self):
        return self._type, self._added

    def _connectSignalsSlots(self):
        self._ui.manageDatabase.clicked.connect(self._openMaterialDatabaseDialog)
        self._ui.filter.textChanged.connect(self._filterChanged)
        self._ui.list.itemSelectionChanged.connect(self._selectionChanged)
        self._ui.createMixture.clicked.connect(self._createMixture)
        self._ui.addMaterials.clicked.connect(self._addMaterials)

    def _load(self):
        phase = None if self._mixture is None else MaterialDB.getPhase(self._mixture).value

        self._ui.list.clear()
        for name, values in MaterialsBase.getMaterials().items():
            if phase is None or values['phase'] == phase:
                MaterialItem(self._ui.list, name, Phase(values['phase']))

    def _selectionChanged(self):
        if self._ui.list.selectedItems():
            self._ui.createMixture.setEnabled(True)
            self._ui.addMaterials.setEnabled(True)
        else:
            self._ui.createMixture.setEnabled(False)
            self._ui.addMaterials.setEnabled(False)

    def _openMaterialDatabaseDialog(self):
        self._dialog = MaterialDatabaseDialog(self)
        self._dialog.accepted.connect(self._load)
        self._dialog.open()

    def _filterChanged(self):
        filterText = self._ui.filter.text().lower()
        for i in range(self._ui.list.count()):
            self._ui.list.item(i).filter(filterText)

    @qasync.asyncSlot()
    async def _createMixture(self):
        materials = self._ui.list.selectedItems()
        if len(materials) == 0:
            return

        species = []
        for item in materials:
            if item.phase() == Phase.SOLID:
                await AsyncMessageBox().information(self, self.tr('Selection Error'),
                                                    self.tr('Only fluid materials can be mixed.'))
                return

            if item.phase() != materials[0].phase():
                await AsyncMessageBox().information(self, self.tr('Selection Error'),
                                                    self.tr('Only materials of the same phase can be mixed.'))
                return

            species.append(item.name())

        with coredb.CoreDB() as db:
            self._added = [MaterialDB.addMixture(db, 'mixture', species)]

        self._type = MaterialType.MIXTURE

        self.accept()

    def _addMaterials(self):
        materials = self._ui.list.selectedItems()
        if len(materials) == 0:
            return

        self._added = []

        with coredb.CoreDB() as db:
            if self._type == MaterialType.NONMIXTURE:
                for item in materials:
                    self._added.append(MaterialDB.addNonMixture(db, item.name()))
            elif self._type == MaterialType.SPECIE:
                for item in materials:
                    self._added.append(MaterialDB.addSpecie(db, item.name(), self._mixture))

        self.accept()
