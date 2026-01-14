#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QGroupBox, QWidget, QVBoxLayout

from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton

from baramFlow.coredb import coredb
from baramFlow.view.setup.boundary_conditions.wall_layers_widget_ui import Ui_WallLayersWidget
from baramFlow.view.widgets.batchable_float_edit import BatchableFloatEdit


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
            BatchableFloatEdit(thickness),
            BatchableFloatEdit(thermalConductivity),
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
        self.widget(Column.THICKNESS).validate(self.tr('Wall Layer Thickness'))
        self.widget(Column.THERMAL_CONDUCTIVITY).validate(self.tr('Wall Layer Thermal Conductivity'))


class WallLayersWidget(QWidget):
    _removeIcon = QIcon(':/icons/trash-outline.svg')

    def __init__(self):
        super().__init__()
        self._ui = Ui_WallLayersWidget()
        self._ui.setupUi(self)

        self._layout = self._ui.wallLayersTable.layout()

        self._rows = []
        
        self._connectSignalsSlots()

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

    def load(self, xpath):
        db = coredb.CoreDB()

        thicknessLayers = db.getValue(xpath + '/thicknessLayers').split()
        thermalConductivityLayers = db.getValue(xpath + '/thermalConductivityLayers').split()

        for i in range(len(thicknessLayers)):
            self.addRow(thicknessLayers[i], thermalConductivityLayers[i])

    async def updateDB(self, db, xpath):
        thicknessLayers = ''
        thermalConductivityLayers = ''

        try:
            for row in self._rows:
                if not row.isHidden():

                    thicknessLayers += row.thickness() + ' '
                    thermalConductivityLayers += row.thermalConductivity() + ' '
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            raise coredb.Cancel

        db.setValue(xpath + '/thicknessLayers', thicknessLayers, self.tr('Thickness'))
        db.setValue(xpath + '/thermalConductivityLayers', thermalConductivityLayers, self.tr('Thermal Conductivity'))

    def validate(self):
        for row in self._rows:
            if not row.isHidden():
                row.validate()

    def _connectSignalsSlots(self):
        self._ui.addWallLayer.clicked.connect(self.addRow)

    def _removeRow(self, index):
        self._rows[index].hide()
        for i in range(index + 1, len(self._rows)):
            self._rows[i].decreaseNO()


class WallLayersBox(QGroupBox):
    def __init__(self, parent):
        super().__init__(parent)

        self._layers = WallLayersWidget()

        layout = QVBoxLayout()
        layout.addWidget(self._layers)
        self.setLayout(layout)

    def isChecked(self):
        return super().isChecked() or not super().isCheckable()

    def load(self, xpath):
        self.setChecked(coredb.CoreDB().getAttribute(xpath, 'disabled') == 'false')
        self._layers.load(xpath)

    async def updateDB(self, db, xpath):
        if self.isChecked():
            db.setAttribute(xpath, 'disabled', 'false')
            await self._layers.updateDB(db, xpath)
        else:
            db.setAttribute(xpath, 'disabled', 'true')

    def validate(self):
        if self.isChecked():
            self._layers.validate()