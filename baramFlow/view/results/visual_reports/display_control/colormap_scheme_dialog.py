#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QListWidgetItem, QHBoxLayout, QLabel, QWidget, QSizePolicy

from baramFlow.view.results.visual_reports.display_control.color_scheme_widget_ui import Ui_ColorSchemeWidget
from .....coredb.color_scheme import ColormapScheme
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .colormap.colormap import colormapName, colormapImage
from .colormap_scheme_dialog_ui import Ui_ColormapSchemeDialog


def createSchemeWidget(img, name):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    image = QLabel()
    image.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
    image.setPixmap(QPixmap(img).scaled(240, 20))
    layout.addWidget(image)
    label = QLabel(name)
    layout.addWidget(label)
    layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)

    return widget

class ColorSchemeWidget(QWidget):
    def __init__(self, scheme: ColormapScheme):
        super().__init__()
        self._ui = Ui_ColorSchemeWidget()
        self._ui.setupUi(self)

        self._ui.image.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
        self._ui.image.setPixmap(QPixmap(colormapImage[scheme]).scaled(240, 20))

        self._ui.name.setText(colormapName[scheme])

        self.scheme = scheme


class ColormapSchemeDialog(ResizableDialog):
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
