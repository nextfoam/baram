#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QFrame, QGridLayout, QWidget, QLabel
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QIcon, QPalette

from widgets.flat_push_button import FlatPushButton


class ListItem(QObject):
    def __init__(self, id_):
        super().__init__()

        self._id = id_
        self._widgets = []

    def columnCount(self):
        return len(self._widgets)

    def id(self):
        return self._id

    def widgets(self):
        return self._widgets

    def widget(self, column):
        return self._widgets[column]


class ListItemWithButtons(ListItem):
    editClicked = Signal()
    removeClicked = Signal()

    def __init__(self, id_: int, texts):
        super().__init__(id_)

        for l in texts:
            self._widgets.append(QLabel(l))

        editButton = FlatPushButton()
        editButton.setIcon(QIcon(':/icons/create-outline.svg'))
        self._widgets.append(editButton)

        removeButton = FlatPushButton(QIcon(':/icons/trash-outline.svg'), '')
        self._widgets.append(removeButton)

        editButton.clicked.connect(self.editClicked)
        removeButton.clicked.connect(self.removeClicked)

    def update(self, texts):
        for i in range(len(texts)):
            self._widgets[i].setText(texts[i])


class ListTable(QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._layout = None
        self._items = {}

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.white)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def setHeaderWithWidth(self, widths):
        if self.layout():
            self._layout = self.layout()
        else:
            self._layout = QGridLayout(self)

        columnCount = len(widths)

        for i in range(columnCount):
            widget = self._layout.itemAtPosition(0, i)
            if widget is None:
                widget = QWidget()
                widget.setMaximumWidth(widths[i])
                self._layout.addWidget(widget, 0, i)

        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self._layout.addWidget(line, 1, 0, 1, columnCount)

    def addItem(self, item: ListItem):
        row = self._layout.rowCount()
        for i in range(item.columnCount()):
            self._layout.addWidget(item.widget(i), row, i)

        self._items[item.id()] = item

    def removeItem(self, id_):
        item = self._items.pop(id_)
        for widget in item.widgets():
            self._layout.removeWidget(widget)
            widget.deleteLater()

    def item(self, id_):
        return self._items[id_]

    def count(self):
        return len(self._items)

    def clear(self):
        for i in [key for key in self._items]:
            self.removeItem(i)

        self._items = {}
