#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QWidget
from PySide6.QtCore import QEvent, QTimer

from app import app
from rendering.vtk_loader import hexPolyData, polyDataToActor, sphereActor, cylinderActor
from openfoam.system.topo_set_dict import HexSource, CylinderSource, SphereSource
from .volume_refine_dialog_ui import Ui_VolumeRefineDialog


class VolumeRefineDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_VolumeRefineDialog()
        self._ui.setupUi(self)

        self._typeRadios = None

        self._gId = None
        self._shape = None

        self._dbElement = None
        self._creationMode = True

        self._connectSignalsSlots()
        self._ui.formStack.setCurrentIndex(0)
        self._ui.ok.hide()
        self._ui.annulusRadius.hide()

        self._actor = None

    def data(self):
        shape = self._ui.shapeRadios.checkedButton().objectName()
        if shape == 'hex':
            return HexSource((float(self._ui.minX.text()), float(self._ui.minY.text()), float(self._ui.minZ.text())),
                              (float(self._ui.maxX.text()), float(self._ui.maxY.text()), float(self._ui.maxZ.text())))
        elif shape == 'cylinder':
            return CylinderSource(
                (float(self._ui.axis1X.text()), float(self._ui.axis1Y.text()), float(self._ui.axis1Z.text())),
                (float(self._ui.axis2X.text()), float(self._ui.axis2Y.text()), float(self._ui.axis2Z.text())),
                float(self._ui.cylinderRadius.text()))
        elif shape == 'sphere':
            return SphereSource(
                (float(self._ui.centerX.text()), float(self._ui.centerY.text()), float(self._ui.centerZ.text())),
                float(self._ui.sphereRadius.text()))

    def event(self, ev):
        if ev.type() == QEvent.LayoutRequest:
            QTimer.singleShot(0, self.adjustSize)
        return super().event(ev)

    def _connectSignalsSlots(self):
        self._ui.minX.editingFinished.connect(self._updateActor)
        self._ui.minY.editingFinished.connect(self._updateActor)
        self._ui.minZ.editingFinished.connect(self._updateActor)
        self._ui.maxX.editingFinished.connect(self._updateActor)
        self._ui.maxY.editingFinished.connect(self._updateActor)
        self._ui.maxZ.editingFinished.connect(self._updateActor)
        self._ui.centerX.editingFinished.connect(self._updateActor)
        self._ui.centerY.editingFinished.connect(self._updateActor)
        self._ui.centerZ.editingFinished.connect(self._updateActor)
        self._ui.sphereRadius.editingFinished.connect(self._updateActor)
        self._ui.axis1X.editingFinished.connect(self._updateActor)
        self._ui.axis1Y.editingFinished.connect(self._updateActor)
        self._ui.axis1Z.editingFinished.connect(self._updateActor)
        self._ui.axis2X.editingFinished.connect(self._updateActor)
        self._ui.axis2Y.editingFinished.connect(self._updateActor)
        self._ui.axis2Z.editingFinished.connect(self._updateActor)
        self._ui.cylinderRadius.editingFinished.connect(self._updateActor)
        self._ui.innerRadius.editingFinished.connect(self._updateActor)
        self._ui.outerRadius.editingFinished.connect(self._updateActor)

        self._ui.next.clicked.connect(self._showVolumeForm)
        self._ui.ok.clicked.connect(self.accept)
        self._ui.cancel.clicked.connect(self.reject)

        self.finished.connect(self._finished)

    def _showVolumeForm(self):
        shape = self._ui.shapeRadios.checkedButton().objectName()
        page = 'hexPage' if shape == 'hex6' else f'{shape}Page'

        self._ui.formStack.setCurrentWidget(self._ui.formStack.findChild(QWidget, page))

        self._ui.next.hide()
        self._ui.ok.show()

        self._updateActor()

    def _updateActor(self):
        if self._actor:
            app.window.renderingView.removeActor(self._actor)

        shape = self._ui.shapeRadios.checkedButton().objectName()
        actor = self._actor
        if shape == 'hex':
            hex = hexPolyData((float(self._ui.minX.text()), float(self._ui.minY.text()), float(self._ui.minZ.text())),
                              (float(self._ui.maxX.text()), float(self._ui.maxY.text()), float(self._ui.maxZ.text())))
            actor = polyDataToActor(hex)
        elif shape == 'cylinder':
            actor = cylinderActor(
                (float(self._ui.axis1X.text()), float(self._ui.axis1Y.text()), float(self._ui.axis1Z.text())),
                (float(self._ui.axis2X.text()), float(self._ui.axis2Y.text()), float(self._ui.axis2Z.text())),
                float(self._ui.cylinderRadius.text()))
        elif shape == 'sphere':
            actor = sphereActor(
                (float(self._ui.centerX.text()), float(self._ui.centerY.text()), float(self._ui.centerZ.text())),
                float(self._ui.sphereRadius.text()))

        app.window.renderingView.addActor(actor)
        app.window.renderingView.refresh()

        self._actor = actor

    def _finished(self):
        if self._actor:
            app.window.renderingView.removeActor(self._actor)
