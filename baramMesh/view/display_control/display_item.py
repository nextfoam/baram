#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QTreeWidgetItem, QLabel, QWidget, QHBoxLayout

from baramMesh.rendering.actor_info import ActorType


class Column(IntEnum):
    NAME_COLUMN = 0
    TYPE_COLUMN = auto()
    COLOR_COLUMN = auto()
    # CUT_ICON_COLUMN = auto()
    # VISIBLE_ICON_COLUMN = auto()


class DisplayItem(QTreeWidgetItem):
    # _emptyIcon = QIcon()
    # _notCutIcon = QIcon(':graphicsIcons/no-cutter.svg')
    # _bulbOnIcon = QIcon(':graphicsIcons/bulb-on.svg')
    # _bulbOffIcon = QIcon(':graphicsIcons/bulb-off.svg')

    _types = {
        ActorType.GEOMETRY: QCoreApplication.translate('DisplayControl', 'Geometry'),
        ActorType.BOUNDARY: QCoreApplication.translate('DisplayControl', 'Boundary'),
        ActorType.MESH: QCoreApplication.translate('DisplayControl', 'Mesh')
    }

    def __init__(self, actorInfo):
        super().__init__()
        self._actorInfo = None
        self._colorWidget = QLabel()

        self._actorInfo = actorInfo
        self.setText(Column.NAME_COLUMN, actorInfo.name())
        self.setText(Column.TYPE_COLUMN, self._types[actorInfo.type()])
        self._updateColorColumn()
        # self._updateCutIcon()
        # self._updateVisibleIcon()

        self._connectSignalsSlots()

    def setupColorWidget(self, parent):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(9, 1, 9, 1)
        layout.addWidget(self._colorWidget)
        # self._colorWidget.setFrameShape(QFrame.Shape.Box)
        self._colorWidget.setMinimumSize(16, 16)
        parent.setItemWidget(self, Column.COLOR_COLUMN, widget)

    def setActorVisible(self, visible):
        self._actorInfo.setVisible(visible)
        self._updateColorColumn()

    def setActorColor(self, color):
        self._actorInfo.setColor(color)
        self._updateColorColumn()

    def setCutEnabled(self, enabled):
        self._actorInfo.setCutEnabled(enabled)
        # self._updateCutIcon()

    def actorInfo(self):
        return self._actorInfo

    def colorWidget(self):
        return self._colorWidget

    def _updateColorColumn(self):
        if self._actorInfo.isVisible():
            color = self._actorInfo.color()
            self._colorWidget.setStyleSheet(
                f'background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 1px solid LightGrey; border-radius: 3px;')
        else:
            self._colorWidget.setStyleSheet('')

    def _updateName(self, name):
        self.setText(Column.NAME_COLUMN, name)
    #
    # def _updateCutIcon(self):
    #     if self._actorInfo.isCutEnabled():
    #         self._colorWidget.clear()
    #     else:
    #         icon = QPixmap(':/icons/lock-closed.svg')
    #         self._colorWidget.setPixmap(icon.scaled(18, 18))
    #
    # def _updateVisibleIcon(self):
    #     if self._actorInfo.isVisible():
    #         self.setIcon(Column.VISIBLE_ICON_COLUMN, self._bulbOnIcon)
    #     else:
    #         self.setIcon(Column.VISIBLE_ICON_COLUMN, self._bulbOffIcon)

    def _connectSignalsSlots(self):
        self._actorInfo.nameChanged.connect(self._updateName)
