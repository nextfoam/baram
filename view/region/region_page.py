#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QVBoxLayout

from app import app
from rendering.point_widget import PointWidget
from view.step_page import StepPage
from .region_form import RegionForm
from .region_card import RegionCard


class RegionPage(StepPage):
    OUTPUT_TIME = 0

    def __init__(self, ui):
        super().__init__(ui, ui.regionPage)
        self._ui = ui
        self._form = RegionForm(ui)

        self._regions = {}
        self._pointWidget = None

        self._loaded = False

        layout = QVBoxLayout(self._ui.regionList)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

    def isNextStepAvailable(self):
        return True

    def lock(self):
        for card in self._regions.values():
            card.disable()

        self._form.disable()

    def unlock(self):
        for card in self._regions.values():
            card.enable()

        self._form.enable()

    def open(self):
        self._load()
        self._updateBounds()

    def selected(self):
        self._load()
        self._form.setupForAdding()
        self._pointWidget.on()
        app.window.meshManager.hide()

    def deselected(self):
        self._pointWidget.off()

    def clearResult(self):
        return

    def _connectSignalsSlots(self):
        self._form.regionAdded.connect(self._add)
        self._form.regionEdited.connect(self._update)

        self._ui.x.editingFinished.connect(self._movePointWidget)
        self._ui.y.editingFinished.connect(self._movePointWidget)
        self._ui.z.editingFinished.connect(self._movePointWidget)
        self._form.pointChanged.connect(self._movePointWidget)
        self._pointWidget.pointMoved.connect(self._setPoint)

    def _load(self):
        if not self._loaded:
            regions = app.db.getElements('region', columns=[])
            for id_ in regions:
                self._add(id_)

            self._loaded = True
            self._updateBounds()

    def _updateBounds(self):
        if not self._pointWidget:
            self._pointWidget = PointWidget(app.window.renderingView)
            self._connectSignalsSlots()

        point = self._pointWidget.setBounds(app.window.geometryManager.getBounds())
        self._setPoint(point)

    def _add(self, id_):
        card = RegionCard(id_)
        self._regions[id_] = card
        card.editClicked.connect(self._form.setupForEditing)
        card.removeClicked.connect(self._remove)
        self._ui.regionList.layout().insertWidget(0, card)

    def _update(self, id_):
        self._regions[id_].load()

    def _remove(self, id_):
        db = app.db.checkout()
        db.removeElement('region', id_)
        app.db.commit(db)

        card = self._regions[id_]
        self._ui.regionList.layout().removeWidget(card)
        card.deleteLater()
        del self._regions[id_]

    def _movePointWidget(self):
        self._setPoint(
            self._pointWidget.setPosition(float(self._ui.x.text()), float(self._ui.y.text()), float(self._ui.z.text())))

    def _setPoint(self, point):
        x, y, z = point
        self._ui.x.setText('{:.6g}'.format(x))
        self._ui.y.setText('{:.6g}'.format(y))
        self._ui.z.setText('{:.6g}'.format(z))
