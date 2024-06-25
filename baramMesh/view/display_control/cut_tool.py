#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonDataModel import vtkPlane

from baramFlow.view.widgets.enum_button_group import EnumButtonGroup
from baramMesh.app import app
from baramMesh.rendering.plane_widget import PlaneWidget


class CutType(Enum):
    CLIP  = auto()
    SLICE = auto()


class ClipPlane(QObject):
    valueChanged = Signal(float)
    valueEditingFinished = Signal()
    stateChanged = Signal(int, int)

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
        self._invert = None

        layout = widget.layout()
        valueWidget = layout.itemAt(self.Item.VALUE.value).widget()
        self._value = valueWidget.layout().itemAt(0).widget()
        self._handle = valueWidget.layout().itemAt(1).widget()
        self._invert = layout.itemAt(self.Item.INVERT.value).widget()

        self._connectSignalsSlots()

    @property
    def handleButton(self):
        return self._handle

    def normalVector(self):
        n = [0, 0, 0]
        if self.invert():
            n[self._normal] = -1
        else:
            n[self._normal] = 1

        return n

    def setOrigin(self, origin):
        self._value.setText('{:.6g}'.format(origin[self._normal]))

    def value(self):
        try:
            return float(self._value.text())
        except ValueError:
            pass

    def clear(self):
        self._checkBox.setChecked(False)

    def isEnabled(self):
        return self._checkBox.isChecked()

    def invert(self):
        return self._invert.isChecked()

    def _connectSignalsSlots(self):
        self._checkBox.stateChanged.connect(self._checkStateChanged)
        self._value.textChanged.connect(self._valueChanged)
        self._value.editingFinished.connect(self.valueEditingFinished)

    def _checkStateChanged(self, checked):
        self._handle.setChecked(False)
        self._widget.setEnabled(checked)
        self.stateChanged.emit(self._normal, checked)

    def _valueChanged(self, value):
        try:
            self.valueChanged.emit(float(value))
        except ValueError:
            pass


class SlicePlane(QObject):
    NO_PLANE = 3

    valueChanged = Signal(float, int)
    valueEditingFinished = Signal()
    handleToggled = Signal(bool)
    normalChanged = Signal(list)

    def __init__(self, ui):
        super().__init__()

        self._plane = ui.slicePlane
        self._widget = ui.sliceBox
        self._value = ui.sliceValue
        self._handle = ui.sliceHandle

        self._connectSignalsSlots()

    def normalVector(self):
        n = [0, 0, 0]
        p = self._plane.currentIndex()
        if p < self.NO_PLANE:
            n[p] = 1

        return n

    def setOrigin(self, origin):
        if self.isEnabled():
            self._value.setText('{:.6g}'.format(origin[self._plane.currentIndex()]))

    def plane(self):
        return self._plane.currentIndex()

    def value(self):
        try:
            return float(self._value.text())
        except ValueError:
            pass

    def clear(self):
        self._plane.setCurrentIndex(self.NO_PLANE)

    def isEnabled(self):
        return self._plane.currentIndex() < self.NO_PLANE

    def handleOff(self):
        self._handle.setChecked(False)

    def _connectSignalsSlots(self):
        self._plane.currentIndexChanged.connect(self._planeChanged)
        self._value.textChanged.connect(self._valueChanged)
        self._value.editingFinished.connect(self.valueEditingFinished)
        self._handle.toggled.connect(self.handleToggled)

    def _planeChanged(self, plane):
        self._widget.setEnabled(plane < self.NO_PLANE)
        self.normalChanged.emit(self.normalVector())

    def _valueChanged(self, value):
        try:
            self.valueChanged.emit(float(value), self._plane.currentIndex())
        except ValueError:
            pass


class CutTool(QObject):
    def __init__(self, ui):
        super().__init__()

        self._widget = ui.cutTool
        self._header = ui.cutHeader
        self._typeRadios = EnumButtonGroup()
        self._clipOption = ui.clipOption
        self._clipHandles = ui.clipHandles
        self._sliceOption = ui.sliceOption
        self._view = ui.renderingView

        self._clipPlanes = {}
        self._slicePlane = SlicePlane(ui)
        self._option = None

        self._bounds = None
        self._planeWidget = PlaneWidget(self._view)
        self._currentHandle = None

        self._header.setContents(ui.cut)

        self._typeRadios.addEnumButton(ui.clip,     CutType.CLIP)
        self._typeRadios.addEnumButton(ui.slice,    CutType.SLICE)

        self._addPlane(ui.cutX, ui.cutXPlane, 0)
        self._addPlane(ui.cutY, ui.cutYPlane, 1)
        self._addPlane(ui.cutZ, ui.cutZPlane, 2)

        self._connectSignalsSlots(ui)

    def option(self):
        return self._option

    def isVisible(self):
        return self._widget.isVisible()

    def hide(self):
        for cut in self._clipPlanes.values():
            cut.clear()
        self._apply()

        self._handleOff()
        self._widget.hide()

    def show(self):
        self._header.setChecked(False)
        self._bounds = app.window.geometryManager.getBounds()
        self._planeWidget.setBounds(self._bounds)
        self._setOrigin(self._bounds.center())
        self._widget.show()
        self._typeChanged(self._typeRadios.checkedData())

    def _addPlane(self, checkBox, widget, normal):
        clipOption = ClipPlane(checkBox, widget, normal)
        self._clipHandles.setId(clipOption.handleButton, normal)
        self._clipPlanes[normal] = clipOption
        clipOption.valueChanged.connect(self._clipOriginChanged)
        clipOption.valueEditingFinished.connect(self._updateOrigin)
        clipOption.stateChanged.connect(self._clipPlaneStateChanged)

    def _connectSignalsSlots(self, ui):
        self._typeRadios.dataChecked.connect(self._typeChanged)
        self._clipHandles.idClicked.connect(self._clipHandleToggled)
        self._slicePlane.valueChanged.connect(self._sliceValueChanged)
        self._slicePlane.valueEditingFinished.connect(self._updateOrigin)
        self._slicePlane.handleToggled.connect(self._sliceHandleToggled)
        self._slicePlane.normalChanged.connect(self._sliceNormalChanged)
        self._planeWidget.planeMoved.connect(self._updateOrigin)
        ui.cutApply.clicked.connect(self._apply)

    def _typeChanged(self, type_):
        self._clipOption.setVisible(type_ == CutType.CLIP)
        self._sliceOption.setVisible(type_ == CutType.SLICE)
        self._handleOff()

    def _clipHandleToggled(self, normal):
        button = self._clipHandles.button(normal)

        for b in self._clipHandles.buttons():
            if b != button:
                b.setChecked(False)

        if button.isChecked():
            self._handleOn(normal)
        else:
            self._handleOff()

        self._view.refresh()

    def _handleOn(self, normal):
        self._planeWidget.on(self._clipPlanes[normal].normalVector())
        self._currentHandle = normal

    def _handleOff(self):
        self._planeWidget.off()
        self._currentHandle = None

    def _setOrigin(self, origin):
        for plane in self._clipPlanes.values():
            plane.setOrigin(origin)

        self._slicePlane.setOrigin(origin)

    def _updateOrigin(self):
        self._setOrigin(self._bounds.toInsidePoint(self._planeWidget.origin()))

    def _origin(self):
        return [plane.value() for plane in self._clipPlanes.values()]

    def _clipOriginChanged(self):
        return self._planeWidget.setOrigin(self._origin())

    def _clipPlaneStateChanged(self, normal, checked):
        if not checked and self._currentHandle == normal:
            self._handleOff()

    def _sliceValueChanged(self, value, plane):
        origin = self._origin()
        origin[plane] = value
        self._planeWidget.setOrigin(origin)

    def _sliceHandleToggled(self, checked):
        if checked:
            self._planeWidget.on(self._slicePlane.normalVector())
        else:
            self._handleOff()

        self._view.refresh()

    def _sliceNormalChanged(self, normal):
        if self._slicePlane.isEnabled():
            self._slicePlane.setOrigin(self._planeWidget.origin())

            if self._planeWidget.isEnabled():
                self._planeWidget.setNormal(normal)
        else:
            self._slicePlane.handleOff()
            # self._planeWidget.off()

    def _apply(self):
        cutType = self._typeRadios.checkedData()
        if cutType == CutType.CLIP:
            planes = []
            for clip in self._clipPlanes.values():
                if clip.isEnabled():
                    plane = vtkPlane()
                    plane.SetOrigin(self._origin())
                    plane.SetNormal(clip.normalVector())
                    planes.append(plane)

            self._option = (cutType, planes)
            if app.window.geometryManager:
                app.window.geometryManager.clip(planes)
            if app.window.meshManager:
                app.window.meshManager.clip(planes)
        else:
            plane = None
            if self._slicePlane.isEnabled():
                plane = vtkPlane()
                plane.SetOrigin(self._origin())
                plane.SetNormal(self._slicePlane.normalVector())

            self._option = (cutType, plane)
            if app.window.geometryManager:
                app.window.geometryManager.slice(plane)
            if app.window.meshManager:
                app.window.meshManager.slice(plane)

