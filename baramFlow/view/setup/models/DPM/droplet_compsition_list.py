#!/usr/bin/env python
# -*- coding: utf-8 -*-

from decimal import Decimal

import qasync
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QIcon, QDoubleValidator
from PySide6.QtWidgets import QTreeWidgetItem, QWidget, QHBoxLayout, QLabel, QLineEdit, QHeaderView

from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.model.DPM_model import DropletCompositionMaterial


addIcon = QIcon(':/icons/add-circle-outline.svg')
removeIcon = QIcon(':/icons/trash-outline.svg')


class PhaseNodeSignals(QObject):
    clicked = Signal()
    changed = Signal()

    def __init__(self):
        super().__init__()


class MaterialNode(QTreeWidgetItem):
    def __init__(self, parent, material, composition):
        super().__init__(parent)

        self.signals = PhaseNodeSignals()

        self._mid = None
        self._composition = QLineEdit(str('0' if composition is None else composition))

        self._button = FlatPushButton(removeIcon, '')

        self._mid, name = material

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(self._button)
        layout.addWidget(QLabel(name))
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)

        self._composition.setValidator(QDoubleValidator())
        self._composition.editingFinished.connect(parent.compositionChanged)

        self.treeWidget().setItemWidget(self, 0, widget)
        self.treeWidget().setItemWidget(self, 1, self._composition)
        #
        # self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)

    def mid(self):
        return self._mid

    def composition(self):
        return self._composition.text()

    @property
    def removeClicked(self):
        return self._button.clicked


class PhaseNode(QTreeWidgetItem):
    def __init__(self, tree, title):
        super().__init__(tree)

        self.signals = PhaseNodeSignals()

        button = FlatPushButton(addIcon, '')
        button.clicked.connect(self.signals.clicked)

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(QLabel(title))
        layout.addWidget(button)
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)

        tree.setItemWidget(self, 0, widget)
        self.setFirstColumnSpanned(True)

    def add(self, material, composition):
        item = MaterialNode(self, material, composition)
        item.removeClicked.connect(lambda: self.removeChild(item))

    def removeChild(self, child):
        super().removeChild(child)
        self.signals.changed.emit()

    def compositionChanged(self):
        self.signals.changed.emit()

    def total(self):
        return sum(Decimal(self.child(i).composition()) for i in range(self.childCount()))


class DropletCompositionList(QObject):
    changed = Signal()

    def __init__(self, parent, tree, solids, liquids):
        super().__init__()

        self._parent = parent
        self._list = tree

        self._solidsRoot = PhaseNode(self._list, self.tr('Solids'))
        self._liquidsRoot = PhaseNode(self._list, self.tr('Liquids'))

        self._selectableSolids = solids
        self._selectableLiquids = liquids

        self._connectSignalsSlots()

        self._list.expandAll()
        self._list.setColumnWidth(1, 80)
        self._list.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._list.header().setStretchLastSection(False)

    def total(self):
        return round(self._solidsRoot.total() + self._liquidsRoot.total(), 6)

    def data(self):
        data = []

        for i in range(self._solidsRoot.childCount()):
            data.append(DropletCompositionMaterial(mid=self._solidsRoot.child(i).mid(),
                                                   composition=self._solidsRoot.child(i).composition()))

        for i in range(self._liquidsRoot.childCount()):
            data.append(DropletCompositionMaterial(mid=self._liquidsRoot.child(i).mid(),
                                                   composition=self._liquidsRoot.child(i).composition()))

        return data

    def addSolid(self, material, composition='0'):
        self._solidsRoot.add(material, composition)

    def addLiquid(self, material, composition='0'):
        self._liquidsRoot.add(material, composition)

    def hasLiquids(self):
        return self._liquidsRoot.childCount() > 0

    def _connectSignalsSlots(self):
        self._solidsRoot.signals.clicked.connect(self._openSolidsSelector)
        self._solidsRoot.signals.changed.connect(self._changed)
        self._liquidsRoot.signals.clicked.connect(self._openLiquidsSelector)
        self._liquidsRoot.signals.changed.connect(self._changed)

    def _openSolidsSelector(self):
        def addSolids():
            for m in self._dialog.selectedItems():
                self.addSolid(m)

        self._dialog = SelectorDialog(self._parent, self.tr("Select Materials"), self.tr("Select Materials"),
                                      self._selectableSolids)
        self._dialog.setMultiSelectionMode()
        self._dialog.accepted.connect(addSolids)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _openLiquidsSelector(self):
        def addLiquid():
            for m in self._dialog.selectedItems():
                self.addLiquid(m)

        if self._selectableLiquids is None:
            await AsyncMessageBox().information(self._parent, self.tr('Cannot Proceed'),
                                                self.tr("Liquid Mixture is not set as the region's material."))
            return

        self._dialog = SelectorDialog(self._parent, self.tr("Select Materials"), self.tr("Select Materials"),
                                      self._selectableLiquids)
        self._dialog.setMultiSelectionMode()
        self._dialog.accepted.connect(addLiquid)
        self._dialog.open()

    def _changed(self):
        self.changed.emit()
