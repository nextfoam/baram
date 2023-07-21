#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QVBoxLayout

from app import app
from libbaram.utils import formatWithSignificants
from rendering.point_widget import PointWidget
from .region_form import RegionForm
from .region_card import RegionCard


class RegionTab(QObject):
    def __init__(self, parent, ui):
        super().__init__()
        self._form = RegionForm(parent, ui)
        self._ui = ui

        self._cards = {}

        self._pointWidget = PointWidget(app.renderingView)

        layout = QVBoxLayout(self._ui.list)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        # geometries = app.window.geometryManager()
        # geometries.showAll()
        point = self._pointWidget.setBounds(app.window.geometryManager().getBounds())
        self._setPoint(point)
        self._pointWidget.on()

        self._connectSignalsSlots()

        self._load()

    def activated(self):
        self._pointWidget.on()

    def deactivated(self):
        self._pointWidget.off()

    def close(self):
        self._pointWidget.close()
        self._pointWidget = None

    def _connectSignalsSlots(self):
        self._form.regionAdded.connect(self._add)
        self._form.regionEdited.connect(self._update)

        self._ui.x.editingFinished.connect(self._movePointWidget)
        self._ui.y.editingFinished.connect(self._movePointWidget)
        self._ui.z.editingFinished.connect(self._movePointWidget)
        self._pointWidget.pointMoved.connect(self._setPoint)

    def _load(self):
        regions = app.db.getElements('region', columns=[])
        for id_ in regions:
            self._add(id_)

    def _add(self, id_):
        card = RegionCard(id_)
        self._cards[id_] = card
        card.editClicked.connect(self._form.setupForEditing)
        card.removeClicked.connect(self._remove)
        self._ui.list.layout().insertWidget(0, card)

    def _update(self, id_):
        self._cards[id_].load()

    def _remove(self, id_):
        db = app.db.checkout()
        db.removeElement('region', id_)
        app.db.commit(db)

        card = self._cards[id_]
        self._ui.list.layout().removeWidget(card)
        card.deleteLater()
        del self._cards[id_]

    def _movePointWidget(self):
        self._setPoint(
            self._pointWidget.setPosition(float(self._ui.x.text()), float(self._ui.y.text()), float(self._ui.z.text())))

    def _setPoint(self, point):
        x, y, z = point
        self._ui.x.setText(formatWithSignificants(x, 4))
        self._ui.y.setText(formatWithSignificants(y, 4))
        self._ui.z.setText(formatWithSignificants(z, 4))

