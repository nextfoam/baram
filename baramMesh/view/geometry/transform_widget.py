#!/usr/bin/env python
# -*- coding: utf-8 -*-
import qasync
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter

from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from .transform_widget_ui import Ui_TransformWidget


class TransformWidget(QWidget):
    transformed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_TransformWidget()
        self._ui.setupUi(self)

        self._meshes = None

        self._connectSignalsSlots()

    def setMeshes(self, sources):
        self._meshes = sources

    def meshes(self):
        return self._meshes

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._ui.tabWidget.setCurrentIndex(0)

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.scale.clicked.connect(self._scale)
        self._ui.rotate.clicked.connect(self._rotate)
        self._ui.translate.clicked.connect(self._translate)

    @qasync.asyncSlot()
    async def _scale(self):
        self._ui.scale.setEnabled(False)

        try:
            x = float(PFloat(self._ui.scaleX.text(), self.tr('Scale Factor')))
            y = float(PFloat(self._ui.scaleY.text(), self.tr('Scale Factor')))
            z = float(PFloat(self._ui.scaleZ.text(), self.tr('Scale Factor')))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        transform = vtkTransform()
        transform.Scale(x, y, z)

        for gId, source in self._meshes.items():
            transformFilter = vtkTransformPolyDataFilter()
            transformFilter.SetInputData(source)
            transformFilter.SetTransform(transform)
            transformFilter.Update()
            self._meshes[gId] = transformFilter.GetOutput()

        self.transformed.emit()

        self._ui.scale.setEnabled(True)

    @qasync.asyncSlot()
    async def _rotate(self):
        self._ui.rotate.setEnabled(False)

        try:
            angle = float(PFloat(self._ui.rotationAngle.text(), self.tr('Rotation Angle')))
            originX = float(PFloat(self._ui.originX.text(), self.tr('Rotation Origin')))
            originY = float(PFloat(self._ui.originY.text(), self.tr('Rotation Origin')))
            originZ = float(PFloat(self._ui.originZ.text(), self.tr('Rotation Origin')))
            axisX = float(PFloat(self._ui.axisX.text(), self.tr('Rotation Axis')))
            axisY = float(PFloat(self._ui.axisY.text(), self.tr('Rotation Axis')))
            axisZ = float(PFloat(self._ui.axisZ.text(), self.tr('Rotation Axis')))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        transform = vtkTransform()
        transform.PostMultiply()
        transform.Translate(-originX, -originY, -originZ)
        transform.RotateWXYZ(angle, axisX, axisY, axisZ)
        transform.Translate(originX, originY, originZ)

        for gId, source in self._meshes.items():
            transformFilter = vtkTransformPolyDataFilter()
            transformFilter.SetInputData(source)
            transformFilter.SetTransform(transform)
            transformFilter.Update()
            self._meshes[gId] = transformFilter.GetOutput()

        self.transformed.emit()

        self._ui.rotate.setEnabled(True)

    @qasync.asyncSlot()
    async def _translate(self):
        self._ui.translate.setEnabled(False)

        try:
            x = float(PFloat(self._ui.translateX.text(), self.tr('Translate Offset')))
            y = float(PFloat(self._ui.translateY.text(), self.tr('Translate Offset')))
            z = float(PFloat(self._ui.translateZ.text(), self.tr('Translate Offset')))
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        transform = vtkTransform()
        transform.Translate(x, y, z)

        for gId, source in self._meshes.items():
            transformFilter = vtkTransformPolyDataFilter()
            transformFilter.SetInputData(source)
            transformFilter.SetTransform(transform)
            transformFilter.Update()
            self._meshes[gId] = transformFilter.GetOutput()

        self.transformed.emit()

        self._ui.translate.setEnabled(True)
