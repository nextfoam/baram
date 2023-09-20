#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from baramSnappy.app import app
from baramSnappy.db.configurations_schema import RegionType
from .region_card_ui import Ui_RegionCard


class RegionCard(QWidget):
    editClicked = Signal(str)
    removeClicked = Signal(str)

    def __init__(self, id_):
        super().__init__()
        self._ui = Ui_RegionCard()
        self._ui.setupUi(self)

        self._id = id_
        self._type = None
        self._point = None

        self._types = {
            RegionType.FLUID.value: self.tr('(Fluid)'),
            RegionType.SOLID.value: self.tr('(Solid)')
        }

        self._connectSignalsSlots()
        self.load()

    def name(self):
        return self._ui.name.text()

    def type(self):
        return self._type

    def point(self):
        return self._point

    def load(self,):
        path = f'region/{self._id}/'

        self._type = app.db.getValue(path + 'type')
        x, y, z = app.db.getVector(path + 'point')
        self._point = float(x), float(y), float(z)

        self._ui.name.setText(app.db.getValue(path + 'name'))
        self._ui.type.setText(self._types[self._type])
        self._ui.point.setText(f'({x}, {y}, {z})')

    def addForm(self, form):
        self._ui.header.setEnabled(False)
        self._ui.card.layout().addWidget(form)

    def removeForm(self, form):
        self._ui.header.setEnabled(True)
        self._ui.card.layout().removeWidget(form)

    def showWarning(self):
        self._ui.warning.show()

    def hideWarning(self):
        self._ui.warning.hide()

    def _connectSignalsSlots(self):
        self._ui.edit.clicked.connect(self._editClicked)
        self._ui.remove.clicked.connect(self._removeClicked)

    def _editClicked(self):
        self.editClicked.emit(self._id)

    def _removeClicked(self):
        self.removeClicked.emit(self._id)
