#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Signal

from baramFlow.coredb.configuraitions import ConfigurationException
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB, MaterialType
from baramFlow.view.widgets.content_page import ContentPage
from .material_add_dialog import MaterialAddDialog
from .material_card import MaterialCard
from .material_page_ui import Ui_MaterialPage
from .mixture_card import MixtureCard


class MaterialPage(ContentPage):
    pageReload = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MaterialPage()
        self._ui.setupUi(self)

        self._cardListLayout = QVBoxLayout(self._ui.cardList)
        self._cardListLayout.addStretch()
        self._cardListLayout.setContentsMargins(0, 0, 0, 0)

        self._addDialog = None

        self._connectSignalsSlots()
        self._load()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self.pageReload.emit()

        return super().showEvent(ev)

    @qasync.asyncSlot()
    async def _remove(self, card: MaterialCard):
        # The count of the layout returns one more than the number of cards, because of the stretch.
        if self._cardListLayout.count() < 3:
            await AsyncMessageBox().information(self, self.tr("Remove material"),
                                                self.tr("At least one material is required and cannot be removed."))
            return

        if not await AsyncMessageBox().confirm(
                self, self.tr("Remove material"), self.tr('Remove material "{}"'.format(card.name))):
            return

        try:
            with coredb.CoreDB() as db:
                MaterialDB.removeMaterial(db, card.mid)
            self._cardListLayout.removeWidget(card)
            card.deleteLater()
        except ConfigurationException as ex:
            await AsyncMessageBox().information(self, self.tr('Material Removal Failed'), str(ex))

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._add)

    def _load(self):
        materials = coredb.CoreDB().getMaterials()

        for mid, name, formula, phase in materials:
            self._addCard(mid)

    def _add(self):
        self._addDialog = MaterialAddDialog(self)
        self._addDialog.accepted.connect(self._addDialogAccepted)
        self._addDialog.open()

    def _addCard(self, mid: str, type_=None):
        if type_ is None:
            type_ = MaterialDB.getType(mid)

        if type_ == MaterialType.NONMIXTURE:
            card = MaterialCard(mid)
        elif type_ == MaterialType.MIXTURE:
            card = MixtureCard(mid)
        else:
            return

        self._cardListLayout.insertWidget(0, card)
        card.load()
        card.removeClicked.connect(self._remove)
        self.pageReload.connect(card.load)

    def _addDialogAccepted(self):
        type_, added = self._addDialog.result()
        for mid in added:
            self._addCard(mid, type_)

