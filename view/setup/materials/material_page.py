#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QVBoxLayout, QMessageBox
from PySide6.QtCore import Signal

from coredb import coredb
from coredb.material_db import MaterialDB
from coredb.project import Project
from coredb.coredb import Error
from view.widgets.selector_dialog import SelectorDialog
from view.widgets.multi_selector_dialog import SelectorItem
from view.widgets.content_page import ContentPage
from .material_page_ui import Ui_MaterialPage
from .material_card import MaterialCard


class MaterialPage(ContentPage):
    pageReload = Signal()

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

        self._materialChanged = Project.instance().materialChanged

        self._connectSignalsSlots()
        self._load()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self.pageReload.emit()

        return super().showEvent(ev)

    def _remove(self, card):
        # The count of the layout returns one more than the number of cards, because of the stretch.
        if self._cardListLayout.count() < 3:
            QMessageBox.information(self, self.tr("Remove material"),
                                    self.tr("At least one material is required and cannot be removed."))
            return

        confirm = QMessageBox.question(
            self, self.tr("Remove material"), self.tr(f'Remove material "{card.name}"'))
        if confirm == QMessageBox.Yes:
            error = self._db.removeMaterial(card.name)
            if not error:
                self._cardListLayout.removeWidget(card)
                card.deleteLater()
            elif error == Error.REFERENCED:
                QMessageBox.critical(
                    self, self.tr('Remove Meterial Failed'),
                    self.tr(f'"{card.name}" is referenced by other configurations. It cannot be removed.'))

        self._materialChanged.emit()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._add)

    def _load(self):
        materials = self._db.getMaterials()

        for mid, name, formula, phase in materials:
            self._addCard(mid)

    def _add(self):
        if self._addDialog is None:
            materials = [
                SelectorItem(f'{name} ({MaterialDB.getPhaseText(MaterialDB.dbTextToPhase(phase))})', name, name)
                for name, formula, phase in self._db.getMaterialsFromDB()]
            self._addDialog = SelectorDialog(self, self.tr("Material"), self.tr("Select material to add"), materials)
            self._addDialog.accepted.connect(self._addDialogAccepted)

        self._addDialog.open()

    def _addCard(self, mid):
        card = MaterialCard(mid)
        self._cardListLayout.insertWidget(0, card)
        card.removeClicked.connect(self._remove)
        self.pageReload.connect(card.load)

    def _addDialogAccepted(self):
        self._addCard(self._db.addMaterial(self._addDialog.selectedItem()))
        self._materialChanged.emit()

