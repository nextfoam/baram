#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QVBoxLayout

from baramMesh.app import app
from baramMesh.view.step_page import StepPage
from baramMesh.db.configurations_schema import CFDType
from .region_form import RegionForm
from .region_card import RegionCard


class RegionPage(StepPage):
    OUTPUT_TIME = 0

    def __init__(self, ui):
        super().__init__(ui, ui.regionPage)

        self._ui = ui
        self._form = None
        self._regions = {}
        self._bounds = None

        self._form = RegionForm(self._ui.renderingView, self)
        self._focusing = self._form

        layout = QVBoxLayout(self._ui.regionList)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        self._ui.regionList.layout().insertWidget(0, self._form)

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        if not self._regions:
            if app.db.elementCount('region') > 0:
                return True

            self._ui.regionEmptyMessage.setVisible(True)
            self._ui.regionValidationMessage.hide()
            return False

        self._ui.regionEmptyMessage.setVisible(False)

        # hasFluid = False
        available = True
        for card in self._regions.values():
            # hasFluid = hasFluid or card.type() == RegionType.FLUID.value
            if not self._bounds.includes(card.point()):
                card.showWarning()
                available = False
            else:
                card.hideWarning()

        multiRegion = len(self._regions) > 1
        hasInterRegionInterface = app.db.elementCount(
            'geometry', lambda i, e: e['cfdType'] == CFDType.INTERFACE.value and e['interRegion']) > 0

        if multiRegion == hasInterRegionInterface:
            self._ui.regionValidationMessage.hide()
            return available

        if multiRegion:
            self._ui.regionValidationMessage.setText(self.tr(
                'No Inter-Region Interface is configured while Region points are configured.'))
        else:
            self._ui.regionValidationMessage.setText(self.tr(
                'Only one Region Point is configured while Inter-Region Interface is configured in Geometry Step.'))
        self._ui.regionValidationMessage.show()

        return False

    def open(self):
        if self._loaded:
            self._updateBounds()
        else:
            self._load()

    async def selected(self):
        if not self._loaded:
            self._load()

        app.window.meshManager.unload()

    def deselected(self):
        self._form.cancel()
        self._ui.regionValidationMessage.hide()

    def removeForm(self, form):
        self._ui.regionList.layout().removeWidget(self._form)
        self._form.setOwner(None)

    def _outputPath(self):
        return None

    def _enableStep(self):
        self._ui.regionAdd.setEnabled(True)

        for card in self._regions.values():
            card.setEnabled(True)

    def _disableStep(self):
        self._ui.regionAdd.setEnabled(False)

        for card in self._regions.values():
            card.setEnabled(False)

    def _clear(self):
        for card in self._regions.values():
            self._ui.regionList.layout().removeWidget(card)
            card.deleteLater()

        self._regions = {}

    def _connectSignalsSlots(self):
        self._ui.regionArea.verticalScrollBar().rangeChanged.connect(self._focus)
        self._ui.regionAdd.clicked.connect(self._showFormForAdding)
        self._form.regionAdded.connect(self._add)
        self._form.regionEdited.connect(self._update)
        self._form.canceled.connect(self._formCanceled)

    def _load(self):
        self._updateBounds()

        regions = app.db.getElements('region')
        for id_ in regions:
            self._add(id_)

        self._loaded = True

    def _updateBounds(self):
        self._bounds = app.window.geometryManager.getBounds()
        self._form.setBounds(self._bounds)

    def _showFormForAdding(self):
        layout = self._ui.regionList.layout()
        if self._form.owner() == self:
            if index := layout.indexOf(self._form):
                layout.takeAt(index)
                layout.insertWidget(0, self._form)
        else:
            self._form.owner().removeForm(self._form)
            layout.insertWidget(0, self._form)

        self._form.setupForAdding()
        self._form.setOwner(self)
        self._showForm()

    def _showFormForEditing(self, id_):
        self._form.owner().removeForm(self._form)
        self._regions[id_].addForm(self._form)
        self._form.setupForEditing(id_)
        self._form.setOwner(self._regions[id_])
        self._showForm()

    def _add(self, id_):
        card = RegionCard(id_)
        self._regions[id_] = card
        card.editClicked.connect(self._showFormForEditing)
        card.removeClicked.connect(self._remove)
        self._ui.regionList.layout().insertWidget(0, card)

        self._moveFocus(card)
        self._updateNextStepAvailable()
        self._form.hide()

    def _update(self, id_):
        self._regions[id_].load()
        self._hideForm()

    def _remove(self, id_):
        db = app.db.checkout()
        db.removeElement('region', id_)
        app.db.commit(db)

        card = self._regions[id_]
        self._ui.regionList.layout().removeWidget(card)
        card.deleteLater()
        del self._regions[id_]

        self._updateNextStepAvailable()

    def _formCanceled(self):
        self._hideForm()

    def _hideForm(self):
        if owner := self._form.owner():
            owner.removeForm(self._form)

        self._ui.regionList.layout().insertWidget(0, self._form)
        self._form.setOwner(self)
        self._form.hide()
        self._updateNextStepAvailable()

    def _showForm(self):
        self._form.show()
        self._moveFocus(self._form)
        self._setNextStepEnabled(False)

    def _moveFocus(self, widget):
        self._focusing = widget
        self._focus()

    def _focus(self):
        if self._focusing.isVisible():
            self._ui.regionArea.ensureWidgetVisible(self._focusing)
