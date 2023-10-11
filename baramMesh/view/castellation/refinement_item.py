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
    LEVEL_COLUMN = auto()


class RefinementItem(QTreeWidgetItem):
    def __init__(self, gId, name, level):
        super().__init__(int(gId))
        self._eyeCheckBox = IconCheckBox(':/icons/eye.svg', ':/icons/eye-off.svg')
        self._editable = True

        self._eyeCheckBox.setChecked(True)
        self.setText(Column.ICON_COLUMN, '')
        self.setText(Column.NAME_COLUMN, name)
        self.setText(Column.LEVEL_COLUMN, level)
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)

        self._eyeCheckBox.toggled.connect(self._eyeToggled)

    def addAsTopLevel(self, tree):
        tree.addTopLevelItem(self)
        self._setupWithTreeWidget()

    def addAsChild(self, parent):
        parent.addChild(self)
        self._setupWithTreeWidget()

    def gId(self):
        return str(self.type())

    def name(self):
        return self.text(Column.NAME_COLUMN)

    def level(self):
        return self.text(Column.LEVEL_COLUMN)

    def isEyeOn(self):
        return self._eyeCheckBox and self._eyeCheckBox.isChecked()

    def isEyeOff(self):
        return self._eyeCheckBox and not self._eyeCheckBox.isChecked()

    def eyeOn(self):
        self._eyeCheckBox.setChecked(True)

    def eyeOff(self):
        self._eyeCheckBox.setChecked(False)

    def enable(self):
        self._editable = True

    def disable(self):
        self._editable = False

    def _setupWithTreeWidget(self):
        self.treeWidget().setItemWidget(self, Column.ICON_COLUMN.value, self._eyeCheckBox)

    def _eyeToggled(self, state):
        if state:
            app.window.geometryManager.showActor(str(self.type()))
        else:
            app.window.geometryManager.hideActor(str(self.type()))
