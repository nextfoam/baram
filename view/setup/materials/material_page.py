#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox

from coredb import coredb
from coredb.material_db import MaterialDB, ListIndex, DBListIndex
from view.widgets.selector_dialog import SelectorDialog
from view.widgets.multi_selector_dialog import SelectorItem
from .material_page_ui import Ui_MaterialPage
from .material_card import MaterialCard


class MaterialPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MaterialPage()
        self._ui.setupUi(self)

        self._cardListLayout = QVBoxLayout(self._ui.cardList)
        self._cardListLayout.setSpacing(0)
        self._cardListLayout.addStretch()
        self._cardListLayout.setContentsMargins(0, 0, 0, 0)

        self._db = coredb.CoreDB()
        self._addDialog = None

        self._connectSignalsSlots()
        self._load()

    def save(self):
        pass

    def _remove(self, card):
        # The count of the layout returns one more than the number of cards, because of the stretch.
        if self._cardListLayout.count() < 3:
            QMessageBox.information(self, self.tr("Remove material"),
                                    self.tr("At least one material is required and cannot be removed."))
            return

        confirm = QMessageBox.question(
            self, self.tr("Remove material"), self.tr(f'Remove material "{card.name}"'))
        if confirm == QMessageBox.Yes:
            self._db.removeMaterial(card.name)
            self._cardListLayout.removeWidget(card)
            card.deleteLater()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._add)

    def _load(self):
        materials = self._db.getMaterials()

        for m in materials:
            self._addCard(m[ListIndex.ID.value])

    def _add(self):
        if self._addDialog is None:
            materials = [SelectorItem(
                f'{m[DBListIndex.NAME.value]} ({MaterialDB.getPhaseText(MaterialDB.dbTextToPhase(m[DBListIndex.PHASE.value]))})',
                m[DBListIndex.NAME.value],
                m[DBListIndex.NAME.value])
                for m in self._db.getMaterialsFromDB()]
            self._addDialog = SelectorDialog(self, self.tr("Material"), self.tr("Select material to add"), materials)
            self._addDialog.accepted.connect(self._addDialogAccepted)

        self._addDialog.open()

    def _addCard(self, mid):
        card = MaterialCard(mid)
        self._cardListLayout.insertWidget(0, card)
        card.removeClicked.connect(self._remove)

    def _addDialogAccepted(self):
        self._addCard(self._db.addMaterial(self._addDialog.selectedItem()))

