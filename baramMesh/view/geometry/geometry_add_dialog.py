#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal

from PySide6.QtWidgets import QDialog

from widgets.enum_button_group import EnumButtonGroup

from baramMesh.db.configurations_schema import Shape
from .geometry_add_dialog_ui import Ui_GeometryAddDialog


class GeometryAddDialog(QDialog):
    shapeSelected = Signal(Shape)

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_GeometryAddDialog()
        self._ui.setupUi(self)

        self._radios = EnumButtonGroup()
        self._radios.addEnumButton(self._ui.hex,        Shape.HEX)
        self._radios.addEnumButton(self._ui.cylinder,   Shape.CYLINDER)
        self._radios.addEnumButton(self._ui.sphere,     Shape.SPHERE)
        self._radios.addEnumButton(self._ui.hex6,       Shape.HEX6)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.next.clicked.connect(self._onAccept)

    def _onAccept(self):
        self.shapeSelected.emit(self._radios.checkedData())

        self.accept()
