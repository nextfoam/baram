#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox

from coredb import coredb
from view.widgets.selector_dialog import SelectorDialog
from .material_page_ui import Ui_MaterialPage
from .material_card import MaterialCard
from .material_db import MaterialDB


class MaterialPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MaterialPage()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._cardListLayout = QVBoxLayout(self._ui.cardList)
        self._cardListLayout.setSpacing(0)
        self._cardListLayout.addStretch()
        self._cardListLayout.setContentsMargins(0, 0, 0, 0)

        self._addDialog = SelectorDialog(self.tr("Material"), self.tr("Select material to add"),
                                         MaterialDB.instance().materialList())

        self._connectSignalsSlots()
        self._load()

    def hideEvent(self, ev):
        if ev.spontaneous():
            return

    def _remove(self, card):
        confirm = QMessageBox.question(
            self, self.tr("Remove material"), self.tr('Remove material "{material}"').format(material=card.name))
        if confirm == QMessageBox.Yes:
            self._cardListLayout.removeWidget(card)
            card.deleteLater()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._add)

    def _load(self):
        self._addMaterial("Air")

    def _add(self):
        if self._addDialog.exec():
            self._addMaterial(self._addDialog.selectedItem())

    def _addMaterial(self, name):
        card = MaterialCard(self, MaterialDB.instance().getMaterial(name))
        self._cardListLayout.insertWidget(0, card)
        card.removeClicked.connect(self._remove)
