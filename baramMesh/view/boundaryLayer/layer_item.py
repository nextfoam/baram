#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from baramMesh.app import app
from baramMesh.view.widgets.icon_check_box import IconCheckBox


class Column(IntEnum):
    ICON_COLUMN = 0
    NAME_COLUMN = auto()
    LAYER_COLUMN = auto()


class LayerItem(QTreeWidgetItem):
    def __init__(self, gId, name, layers):
        super().__init__(int(gId))
        self._eyeCheckBox = IconCheckBox(':/icons/eye.svg', ':/icons/eye-off.svg')
        self._editable = True

        self._eyeCheckBox.setChecked(True)
        self.setText(Column.ICON_COLUMN, '')
        self.setText(Column.NAME_COLUMN, name)
        self.setText(Column.LAYER_COLUMN, layers)
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)

        self._eyeCheckBox.toggled.connect(self._eyeToggled)

    def addTo(self, tree):
        tree.addTopLevelItem(self)
        self.treeWidget().setItemWidget(self, Column.ICON_COLUMN.value, self._eyeCheckBox)

    def gId(self):
        return str(self.type())

    def name(self):
        return self.text(Column.NAME_COLUMN)

    def setLayers(self, layers):
        self.setText(Column.LAYER_COLUMN, layers)

    def isEyeOn(self):
        return self._eyeCheckBox and self._eyeCheckBox.isChecked()

    def isEyeOff(self):
        return self._eyeCheckBox and not self._eyeCheckBox.isChecked()

    def eyeOn(self):
        self._eyeCheckBox.setChecked(True)

    def eyeOff(self):
        self._eyeCheckBox.setChecked(False)

    def lock(self):
        self._editable = False

    def unlock(self):
        self._editable = True

    def _eyeToggled(self, state):
        if state:
            app.window.geometryManager.showActor(str(self.type()))
        else:
            app.window.geometryManager.hideActor(str(self.type()))
