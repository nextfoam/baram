#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.material_db import MaterialDB, MaterialType
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
from widgets.async_message_box import AsyncMessageBox
from .material_add_dialog import MaterialAddDialog
from .material_card import MaterialCard
from .mixture_card_ui import Ui_MixtureCard
from .mixture_dialog import MixtureDialog


class MixtureCard(QWidget):
    removeClicked = Signal(QWidget)

    def __init__(self, mid):
        super().__init__()
        self._ui = Ui_MixtureCard()
        self._ui.setupUi(self)

        self._mid = mid
        self._dialog = None
        self._addDialog = None

        self._xpath = MaterialDB.getXPath(mid)

        self._primarySpecie = None
        self._cardListLayout = QVBoxLayout()

        widget = QWidget()
        widget.setLayout(self._cardListLayout)
        self._cardListLayout.setContentsMargins(0, 0, 0, 0)
        self._cardListLayout.setSpacing(0)
        self._ui.frame.layout().addWidget(widget)

        self._connectSignalsSlots()

        for mid, name in coredb.CoreDB().getSpecies(self._mid):
            self._addCard(mid)

    @property
    def type(self):
        return MaterialType.MIXTURE

    @property
    def mid(self):
        return self._mid

    @property
    def name(self):
        return self._ui.name.text()

    def load(self):
        if not ModelsDB.isSpeciesModelOn():
            self.hide()
            return

        db = coredb.CoreDB()

        self._ui.name.setText(MaterialDB.getName(self._mid))

        self._ui.densitySpec.setText(
            MaterialDB.dbSpecificationToText(db.getValue(self._xpath + '/density/specification')))

        energyModelOn = ModelsDB.isEnergyModelOn()
        if energyModelOn:
            self._ui.specificHeatWidget.show()
            self._ui.specificHeatSpec.setText(
                MaterialDB.dbSpecificationToText(db.getValue(self._xpath + '/specificHeat/specification')))
        else:
            self._ui.specificHeatWidget.hide()

        if energyModelOn or ModelsDB.getTurbulenceModel() != TurbulenceModel.INVISCID:
            self._ui.transportSpec.setText(
                MaterialDB.dbSpecificationToText(db.getValue(self._xpath + '/viscosity/specification')))
        else:
            self._ui.transportWidget.hide()

        self._ui.massDiffusivity.setText(db.getValue(self._xpath + '/mixture/massDiffusivity'))

        self._primarySpecie = db.getValue(self._xpath + '/mixture/primarySpecie')
        self._ui.primarySpecie.setText(MaterialDB.getName(self._primarySpecie))

        for i in range(self._cardListLayout.count()):
            self._cardListLayout.itemAt(i).widget().load()

        self.show()

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._edit)
        self._ui.remove.clicked.connect(self._remove)
        self._ui.addSpecies.clicked.connect(self._addSpecies)

    def _edit(self):
        self._dialog = MixtureDialog(self, self._mid)
        self._dialog.accepted.connect(self.load)
        self._dialog.open()

    def _remove(self):
        self.removeClicked.emit(self)

    def _addSpecies(self):
        self._addDialog = MaterialAddDialog(self, self._mid)
        self._addDialog.accepted.connect(self._addDialogAccepted)
        self._addDialog.open()

    @qasync.asyncSlot()
    async def _removeSpecie(self, card):
        if self._cardListLayout.count() < 2:
            await AsyncMessageBox().information(self, self.tr("Remove specie"),
                                                self.tr("At least one specie is required and cannot be removed."))
            return

        if not await AsyncMessageBox().confirm(
                self, self.tr("Remove specie"), self.tr('Remove specie "{}"'.format(card.name))):
            return

        writer = CoreDBWriter()
        writer.callFunction('removeMaterial', [card.name])

        primarySpecie = self._primarySpecie
        if self._primarySpecie == str(card.mid):
            card1 = self._cardListLayout.itemAt(0).widget()
            card2 = self._cardListLayout.itemAt(1).widget()
            primaryCard = card2 if card1.name == card.name else card1
            primarySpecie = primaryCard.name
            writer.append(self._xpath + '/mixture/primarySpecie', str(primaryCard.mid), None)

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Remove Specie Failed"), writer.firstError().toMessage())
            return

        self._ui.primarySpecie.setText(primarySpecie)
        self._cardListLayout.removeWidget(card)
        card.deleteLater()

    def _addCard(self, mid):
        card = MaterialCard(mid)
        card.removeClicked.connect(self._removeSpecie)
        self._cardListLayout.insertWidget(0, card)
        return card

    def _addDialogAccepted(self):
        _, mids = self._addDialog.result()
        for mid in mids:
            self._addCard(mid).load()

