#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel

from baramFlow.coredb import coredb
from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton
from widgets.typed_edit import FloatEdit


class Column(IntEnum):
    NO                      = 0
    THICKNESS               = auto()
    THERMAL_CONDUCTIVITY    = auto()
    REMOVE                  = auto()


class WallLayerItem(QObject):
    removeClicked = Signal()

    _removeIcon = QIcon(':/icons/trash-outline.svg')

    def __init__(self, no, thickness='', thermalConductivity=''):
        super().__init__()

        self._widgets = None
        self._hidden = False

        if no > 1:
            removeButton = FlatPushButton(self._removeIcon, '')
            removeButton.clicked.connect(self.removeClicked)
        else:
            removeButton = QLabel()

        self._widgets = [
            QLabel(str(no)),
            FloatEdit(thickness),
            FloatEdit(thermalConductivity),
            removeButton]

    def thickness(self):
        return self.widget(Column.THICKNESS).text().strip()

    def thermalConductivity(self):
        return self.widget(Column.THERMAL_CONDUCTIVITY).text().strip()

    def widget(self, column):
        return self._widgets[column]

    def no(self):
        return int(self._widgets[Column.NO].text())

    def isHidden(self):
        return self._hidden

    def hide(self):
        self._hidden = True
        for widget in self._widgets:
            widget.hide()

    def decreaseNO(self):
        if not self._hidden:
            self._widgets[Column.NO].setText(str(self.no() - 1))

    def validate(self):
        if not self.thickness():
            self.widget(Column.THICKNESS).setFocus()
            return False, self.tr('Wall Layer Thickness cannot be empty.')

        if not self.thermalConductivity():
            self.widget(Column.THERMAL_CONDUCTIVITY).setFocus()
            return False, self.tr('Wall Layer Thermal Conductivity cannot be empty.')

        return True, None


class WallLayersWidget(QObject):
    _removeIcon = QIcon(':/icons/trash-outline.svg')

    def __init__(self, parent, ui, xpath):
        super().__init__()

        self._parent = parent
        self._groupBox = ui.wallLayers
        self._layout = ui.wallLayersTable.layout()

        self._xpath = xpath

        self._rows = []

        ui.addWallLayer.clicked.connect(self.addRow)

    def addRow(self, thickness='', thermalConductivity=''):
        index = len(self._rows)
        lastNO = 0
        for i in range(index - 1, -1, -1):
            if not self._rows[i].isHidden():
                lastNO = self._rows[i].no()
                break

        item = WallLayerItem(lastNO + 1, thickness, thermalConductivity)
        item.removeClicked.connect(lambda: self._removeRow(index))
        self._rows.append(item)

        row = index + 1    # header row
        for c in range(self._layout.columnCount()):
            self._layout.addWidget(item.widget(c), row, c)

    def load(self):
        db = coredb.CoreDB()

        thicknessLayers = db.getValue(self._xpath + '/thicknessLayers').split()
        thermalConductivityLayers = db.getValue(self._xpath + '/thermalConductivityLayers').split()

        self._groupBox.setChecked(db.getAttribute(self._xpath, 'disabled') == 'false')

        for i in range(len(thicknessLayers)):
            self.addRow(thicknessLayers[i], thermalConductivityLayers[i])

    async def updateDB(self, db):
        thicknessLayers = ''
        thermalConductivityLayers = ''

        for row in self._rows:
            if not row.isHidden():
                valid, msg = row.validate()
                if not valid:
                    await AsyncMessageBox().information(self._parent, self.tr('Input Error'), msg)
                    return False

                thicknessLayers += row.thickness() + ' '
                thermalConductivityLayers += row.thermalConductivity() + ' '

        db.setAttribute(self._xpath, 'disabled', 'false' if self._groupBox.isChecked() else 'true')
        db.setValue(self._xpath + '/thicknessLayers', thicknessLayers, self.tr('Thickness'))
        db.setValue(self._xpath + '/thermalConductivityLayers', thermalConductivityLayers, self.tr('Thermal Conductivity'))

        return True

    def _removeRow(self, index):
        self._rows[index].hide()
        for i in range(index + 1, len(self._rows)):
            self._rows[i].decreaseNO()
