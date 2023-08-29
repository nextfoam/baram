#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from app import app
from db.configurations_schema import RegionType
from .region_card_ui import Ui_RegionCard


class RegionCard(QWidget):
    editClicked = Signal(str)
    removeClicked = Signal(str)

    def __init__(self, id_):
        super().__init__()
        self._ui = Ui_RegionCard()
        self._ui.setupUi(self)

        self._id = id_

        self._types = {
            RegionType.FLUID.value: self.tr('(Fluid)'),
            RegionType.SOLID.value: self.tr('(Solid)')
        }

        self._connectSignalsSlots()
        self.load()

    def name(self):
        return self._ui.name.text()

    def load(self,):
        path = f'region/{self._id}/'
        self._ui.name.setText(app.db.getValue(path + 'name'))
        self._ui.type.setText(self._types[app.db.getValue(path + 'type')])
        x, y, z = app.db.getVector(path + 'point')
        self._ui.point.setText(f'({x}, {y}, {z})')

    def enable(self):
        self._ui.remove.setEnabled(True)

    def disable(self):
        self._ui.remove.setEnabled(False)

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._editClicked)
        self._ui.remove.clicked.connect(self._removeClicked)

    def _editClicked(self):
        self.editClicked.emit(self._id)

    def _removeClicked(self):
        self.removeClicked.emit(self._id)
