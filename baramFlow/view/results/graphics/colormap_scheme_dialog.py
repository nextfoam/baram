#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QListWidgetItem, QHBoxLayout, QLabel, QWidget, QSizePolicy

from baramFlow.base.graphic.color_scheme import ColorbarWidget, ColormapScheme
from baramFlow.base.graphic.color_scheme import colormapName
from .colormap_scheme_dialog_ui import Ui_ColormapSchemeDialog


class ColorSchemeWidget(QWidget):
    def __init__(self, scheme: ColormapScheme):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(9)

        self._colorbarWidget = ColorbarWidget(scheme, 240, 20)
        self._colorbarWidget.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed))
        layout.addWidget(self._colorbarWidget)

        self.title = QLabel()
        self.title.setText(colormapName[scheme])
        self.title.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.title.setMinimumSize(150, 20)
        self.title.setMaximumSize(150, 20)
        layout.addWidget(self.title)

        self.scheme = scheme


class ColormapSchemeDialog(QDialog):
    schemeSelected = Signal(ColormapScheme)

    def __init__(self, parent, currentScheme):
        super().__init__(parent)
        self._ui = Ui_ColormapSchemeDialog()
        self._ui.setupUi(self)

        for scheme in ColormapScheme:
            item = QListWidgetItem(self._ui.schemes)
            widget = ColorSchemeWidget(scheme)
            item.setSizeHint(widget.sizeHint())
            self._ui.schemes.addItem(item)
            self._ui.schemes.setItemWidget(item, widget)
            if scheme == currentScheme:
                item.setSelected(True)

        self._ui.schemes.setFixedHeight(self._ui.schemes.sizeHintForRow(0) * self._ui.schemes.count() + 10)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.schemes.itemSelectionChanged.connect(self._changed)
        self._ui.schemes.itemDoubleClicked.connect(self._doubleClicked)
        self._ui.ok.clicked.connect(self._accept)

    def _changed(self):
        self._ui.ok.setEnabled(True)

    def _doubleClicked(self, item):
        item.setSelected(True)
        self._accept()

    def _accept(self):
        items = self._ui.schemes.selectedItems()
        if len(items) > 0:
            widget: ColorSchemeWidget = self._ui.schemes.itemWidget(items[0])
            self.schemeSelected.emit(ColormapScheme(widget.scheme))

        super().accept()
