#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QTreeWidgetItem, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Signal, QObject, QCoreApplication
from PySide6.QtGui import QIcon, QPixmap

from db.configurations_schema import CFDType, GeometryType
from view.widgets.icon_check_box import IconCheckBox
from view.widgets.flat_push_button import FlatPushButton

VOLUME_ICON_FILE = ':/icons/prism-outline.svg'
SURFACE_ICON_FILE = ':/icons/prism.svg'

CFDTypes = {
    CFDType.NONE.value: QCoreApplication.translate('GeometryPage', 'None'),
    CFDType.CELL_ZONE.value: QCoreApplication.translate('GeometryPage', 'CellZone'),
    CFDType.BOUNDARY.value: QCoreApplication.translate('GeometryPage', 'Boundary'),
    CFDType.CONFORMAL_MESH.value: QCoreApplication.translate('GeometryPage', 'Interface'),
    CFDType.NON_CONFORMAL_MESH.value: QCoreApplication.translate('GeometryPage', 'Intefarce')
}


class GeometryNameWidget(QWidget):
    def __init__(self, name):
        super().__init__()

        icon = QPixmap(SURFACE_ICON_FILE).scaled(16, 16)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        label = QLabel()
        label.setPixmap(icon)
        label.setSizePolicy(sizePolicy)

        self._nameLabel = QLabel(name)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(label)
        layout.addWidget(self._nameLabel)

    def setText(self, text):
        self._nameLabel.setText(text)


class GeometryItem(QTreeWidgetItem):
    def __init__(self, gId):
        super().__init__(int(gId))
        self._eyeCheckBox = None
        self._nameWidget = None

    def gId(self):
        return str(self.type())

    def setCheckBox(self, checkBox):
        self._eyeCheckBox = checkBox

    def setNameWidget(self, widget):
        self._nameWidget = widget

    def updateGeometry(self, geometry):
        if self._nameWidget:
            self._nameWidget.setText(geometry['name'])
        else:
            self.setText(2, geometry['name'])

        self.setText(3, CFDTypes[geometry['cfdType']])

    def isEyeOn(self):
        return self._eyeCheckBox and self._eyeCheckBox.isChecked()

    def isEyeOff(self):
        return self._eyeCheckBox and not self._eyeCheckBox.isChecked()

    def eyeOn(self):
        self._eyeCheckBox.setChecked(True)

    def eyeOff(self):
        self._eyeCheckBox.setChecked(False)


class GeometryList(QObject):
    eyeToggled = Signal(str, bool)

    showAllClicked = Signal()
    hideAllClicked = Signal()
    itemDoubleClicked = Signal(str)

    volumeIcon = QIcon(VOLUME_ICON_FILE)
    surfaceIcon = QIcon(SURFACE_ICON_FILE)

    def __init__(self, tree, geometries):
        super().__init__()
        self._tree = tree
        self._eyeBottons = QWidget(self._tree.header())
        self._eyeOn = FlatPushButton(self._eyeBottons)
        self._eyeOff = FlatPushButton(self._eyeBottons)

        self._items = {}

        self._tree.setColumnWidth(0, 0)
        self._tree.setColumnWidth(1, 60)

        self._eyeOn.setIcon(QIcon(':/icons/eye.svg'))
        self._eyeOff.setIcon(QIcon(':/icons/eye-off.svg'))
        layout = QHBoxLayout(self._eyeBottons)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._eyeOn)
        layout.addWidget(self._eyeOff)

        self._headerPositionChanged()

        self._connectSignalsSlots()

        for gId, geometry in geometries.geometries().items():
            self.add(gId, geometry)

    def add(self, gId, geometry):
        item = GeometryItem(gId)

        if geometry['volume']:
            self._items[geometry['volume']].addChild(item)
            nameWidget = GeometryNameWidget(geometry['name'])
            self._tree.setItemWidget(item, 2, nameWidget)
            item.setNameWidget(nameWidget)
        else:
            self._tree.addTopLevelItem(item)
            item.setIcon(2, self.volumeIcon if geometry['gType'] == GeometryType.VOLUME.value else self.surfaceIcon)
            item.setText(2, geometry['name'])
            item.setExpanded(True)

        if geometry['gType'] == GeometryType.SURFACE.value:
            checkBox = IconCheckBox(':/icons/eye.svg', ':/icons/eye-off.svg')
            checkBox.setChecked(True)
            item.setCheckBox(checkBox)
            checkBox.checkStateChanged.connect(lambda state: self.eyeToggled.emit(gId, state))
            self._tree.setItemWidget(item, 1, checkBox)

        item.setText(3, CFDTypes[geometry['cfdType']])

        self._items[gId] = item

    def update(self, gId, geometry):
        self._items[gId].updateGeometry(geometry)

    def remove(self, gId):
        index = -1
        for i in range(self._tree.topLevelItemCount()):
            if self._tree.topLevelItem(i).gId() == gId:
                index = i
                break

        if index > -1:
            item = self._tree.takeTopLevelItem(index)
            while item.childCount():
                citem = item.takeChild(0)
                del self._items[str(citem.gId())]
                del citem

            del self._items[str(gId)]
            del item

    def currentGeometryID(self):
        return str(self._tree.currentItem().gId()) if self._tree.currentItem() else None

    def childSurfaces(self, gId):
        item = self._items[gId]
        for i in range(item.childCount()):
            yield str(item.child(i).type())

    def _connectSignalsSlots(self):
        self._tree.header().sectionResized.connect(self._headerPositionChanged)
        self._tree.header().sectionMoved.connect(self._headerPositionChanged)
        self._tree.itemDoubleClicked.connect(self._doubleClicked)
        self._eyeOn.clicked.connect(self._showAllActors)
        self._eyeOff.clicked.connect(self._hideAllActors)

    def _headerPositionChanged(self):
        self._eyeBottons.move(self._tree.header().sectionPosition(1), 3)

    def _doubleClicked(self, item, column):
        self.itemDoubleClicked.emit(item.gId())

    def _showAllActors(self):
        for gId in self._items:
            if self._items[gId].isEyeOff():
                self._items[gId].eyeOn()

    def _hideAllActors(self):
        for gId in self._items:
            if self._items[gId].isEyeOn():
                self._items[gId].eyeOff()
