#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox

from view.setup.materials.material_card import MaterialCard
from view.setup.materials.material_db import MaterialDB
from view.setup.materials.material_page_ui import Ui_MaterialPage
from view.widgets.selector_dialog import SelectorDialog


class MaterialPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ui = Ui_MaterialPage()
        self._ui.setupUi(self)
        self._cardListLayout = QVBoxLayout(self._ui.cardList)
        self._cardListLayout.setSpacing(0)
        self._cardListLayout.setContentsMargins(0, 0, 0, 0)

        self._addDialog = SelectorDialog(self.tr("Select material to add"), MaterialDB.instance().materialList())

        self._connectSignalsSlots()

    def init(self):
        pass

    def load(self):
        self._cardListLayout.addStretch()
        self._addMaterial("Air")

    def save(self):
        pass

    def add(self):
        if self._addDialog.exec():
            self._addMaterial(self._addDialog.selectedItem())

    def edit(self, card):
        pass

    def remove(self, card):
        confirm = QMessageBox.question(
            self, self.tr("Remove material"), self.tr('Remove material "{material}"').format(material=card.name))
        if confirm == QMessageBox.Yes:
            self._cardListLayout.removeWidget(card)
            card.deleteLater()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self.add)

    def _addMaterial(self, name):
        self._cardListLayout.insertWidget(0, MaterialCard(self, MaterialDB.instance().getMaterial(name)))
