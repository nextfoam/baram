#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QDoubleValidator
from vtkmodules.vtkCommonDataModel import vtkPlane

from baramSnappy.app import app
from baramSnappy.rendering.plane_widget import PlaneWidget


@dataclass
class Cutter:
    plane: vtkPlane
    invert: bool


class Cut(QObject):
    valueChanged = Signal()
    stateChanged = Signal(int, float)

    class Item(Enum):
        VALUE = 0
        # SLICE_ONLY = auto()
        INVERT = auto()

    def __init__(self, checkBox, widget, normal):
        super().__init__()

        self._checkBox = checkBox
        self._widget = widget
        self._normal = normal
        self._value = None
        self._handle = None
        # self._sliceOnly = None
        self._invert = None

        layout = widget.layout()
        valueWidget = layout.itemAt(self.Item.VALUE.value).widget()
        self._value = valueWidget.layout().itemAt(0).widget()
        self._handle = valueWidget.layout().itemAt(1).widget()
        # self._sliceOnly = layout.itemAt(self.Item.SLICE_ONLY.value).widget()
        self._invert = layout.itemAt(self.Item.INVERT.value).widget()

        self._value.setValidator(QDoubleValidator())

        self._connectSignalsSlots()

    @property
    def handleButton(self):
        return self._handle

    def normalVector(self):
        return [1 if self._normal == i else 0 for i in range(0, 3)]

    def setOrigin(self, origin):
        self._value.setText('{:.6g}'.format(origin[self._normal]))

    def value(self):
        return float(self._value.text())

    def disable(self):
        self._checkBox.setChecked(False)

    def isEnabled(self):
        return self._checkBox.isChecked()
    #
    # def sliceOnly(self):
    #     return self._sliceOnly.isChecked()

    def invert(self):
        return self._invert.isChecked()

    def _connectSignalsSlots(self):
        self._checkBox.stateChanged.connect(self._checkStateChanged)
        self._value.editingFinished.connect(self.valueChanged.emit)

    def _checkStateChanged(self, checked):
        self._handle.setChecked(False)
        self._widget.setEnabled(checked)
        self.stateChanged.emit(self._normal, checked)


class CutTool(QObject):
    def __init__(self, ui):
        super().__init__()

        self._widget = ui.cutTool
        self._header = ui.cutHeader
        self._handles = ui.cutHandles
        self._view = ui.renderingView
        self._cuts = {}
        self._cutters = None

        self._planeWidget = PlaneWidget(self._view)
        self._currentHandle = None

        self._header.setContents(ui.cut)

        self._addPlane(ui.cutX, ui.cutXPlane, 0)
        self._addPlane(ui.cutY, ui.cutYPlane, 1)
        self._addPlane(ui.cutZ, ui.cutZPlane, 2)

        self._connectSignalsSlots(ui)

    def cutters(self):
        return self._cutters

    def isVisible(self):
        return self._widget.isVisible()

    def hide(self):
        for cut in self._cuts.values():
            cut.disable()
        self._apply()

        self._handleOff()
        self._widget.hide()

    def show(self):
        self._header.setChecked(False)
        bounds = app.window.geometryManager.getBounds()
        self._planeWidget.setBounds(bounds)
        self._movePlaneWidget(bounds.center())
        self._widget.show()

    def _addPlane(self, checkBox, widget, normal):
        cut = Cut(checkBox, widget, normal)
        self._handles.setId(cut.handleButton, normal)
        self._cuts[normal] = cut
        cut.valueChanged.connect(self._originChanged)
        cut.stateChanged.connect(self._cutStateChanged)

    def _connectSignalsSlots(self, ui):
        self._handles.idClicked.connect(self._handleToggled)
        self._planeWidget.planeMoved.connect(self._setOrigin)
        ui.cutApply.clicked.connect(self._apply)

    def _handleToggled(self, normal):
        button = self._handles.button(normal)

        for b in self._handles.buttons():
            if b != button:
                b.setChecked(False)

        if button.isChecked():
            self._handleOn(normal)
        else:
            self._handleOff()

        self._view.refresh()

    def _handleOn(self, normal):
        self._planeWidget.on(self._cuts[normal].normalVector())
        self._currentHandle = normal

    def _handleOff(self):
        self._planeWidget.off()
        self._currentHandler = None

    def _setOrigin(self, origin):
        for cut in self._cuts.values():
            cut.setOrigin(origin)

    def _origin(self):
        return [plane.value() for plane in self._cuts.values()]

    def _originChanged(self):
        self._movePlaneWidget(self._origin())

    def _movePlaneWidget(self, origin):
        self._setOrigin(self._planeWidget.setOrigin(origin))

    def _cutStateChanged(self, normal, checked):
        if not checked and self._currentHandle == normal:
            self._handleOff()

    def _apply(self):
        self._cutters = []
        for cut in self._cuts.values():
            if cut.isEnabled():
                plane = vtkPlane()
                plane.SetOrigin(self._origin())
                plane.SetNormal(cut.normalVector())

                self._cutters.append(Cutter(plane, cut.invert()))
                # if cut.sliceOnly():
                #     self._cutters.append(Cutter(plane, not cut.invert()))

        if app.window.geometryManager:
            app.window.geometryManager.cut(self._cutters)
        if app.window.meshManager:
            app.window.meshManager.cut(self._cutters)
