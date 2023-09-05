#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QVBoxLayout

from app import app
from view.step_page import StepPage
from .region_form import RegionForm
from .region_card import RegionCard


class RegionPage(StepPage):
    OUTPUT_TIME = 0

    def __init__(self, ui):
        super().__init__(ui, ui.regionPage)
        self._ui = ui
        self._form = None

        self._regions = {}
        self._loaded = False

        self._form = RegionForm(self._ui.renderingView)

        layout = QVBoxLayout(self._ui.regionList)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return app.db.elementCount('region') > 0

    def lock(self):
        self._ui.regionAdd.setEnabled(False)

        for card in self._regions.values():
            card.setEnabled(False)

    def unlock(self):
        self._ui.regionAdd.setEnabled(True)

        for card in self._regions.values():
            card.setEnabled(True)

    def open(self):
        self._load()
        self._updateBounds()

    def selected(self):
        self._load()
        app.window.meshManager.hide()

    def deselected(self):
        self._form.hide()

    def clearResult(self):
        return

    def _connectSignalsSlots(self):
        self._ui.regionAdd.clicked.connect(self._showFormForAdding)
        self._form.regionAdded.connect(self._add)
        self._form.regionEdited.connect(self._update)

    def _load(self):
        if not self._loaded:
            regions = app.db.getElements('region', columns=[])
            for id_ in regions:
                self._add(id_)

            self._loaded = True
            self._updateBounds()

    def _updateBounds(self):
        self._form.setBounds(app.window.geometryManager.getBounds())

    def _add(self, id_):
        card = RegionCard(id_)
        self._regions[id_] = card
        card.editClicked.connect(self._showFormForEditing)
        card.removeClicked.connect(self._remove)
        self._ui.regionList.layout().insertWidget(0, card)

        self._updateNextStepAvailable()
        self._ui.regionList.layout().removeWidget(self._form)
        self._form.hide()

    def _update(self, id_):
        self._regions[id_].load()
        self._regions[id_].removeForm(self._form)

    def _remove(self, id_):
        db = app.db.checkout()
        db.removeElement('region', id_)
        app.db.commit(db)

        card = self._regions[id_]
        self._ui.regionList.layout().removeWidget(card)
        card.deleteLater()
        del self._regions[id_]

        self._updateNextStepAvailable()

    def _showFormForAdding(self):
        self._form.setupForAdding()
        self._ui.regionList.layout().insertWidget(0, self._form)
        self._form.show()

    def _showFormForEditing(self, id_):
        self._form.setupForEditing(id_)
        self._regions[id_].showForm(self._form)
        self._form.show()
