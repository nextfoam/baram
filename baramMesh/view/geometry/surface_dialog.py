#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog
from vtkmodules.vtkCommonColor import vtkNamedColors

from libbaram.simple_db.simple_schema import ValidationError
from widgets.async_message_box import AsyncMessageBox
from widgets.enum_button_group import EnumButtonGroup

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType
from baramMesh.rendering.vtk_loader import polyDataToActor
from .geometry import RESERVED_NAMES
from .surface_dialog_ui import Ui_SurfaceDialog
from .transform_widget import TransformWidget


class SurfaceDialog(QDialog):
    def __init__(self, parent, renderingView):
        super().__init__(parent)
        self._ui = Ui_SurfaceDialog()
        self._ui.setupUi(self)

        self._renderingView = renderingView
        self._typeRadios = EnumButtonGroup()

        self._transformWidget = TransformWidget(self)

        self._gIds = None
        self._dbElement = None

        self._sources = None
        self._actors = []

        self._editable = True
        self._transformed = False

        self._typeRadios.addEnumButton(self._ui.none,       CFDType.NONE)
        self._typeRadios.addEnumButton(self._ui.boundary,   CFDType.BOUNDARY)
        self._typeRadios.addEnumButton(self._ui.interface_, CFDType.INTERFACE)

        self._ui.dialogContent.layout().addWidget(self._transformWidget)

        self._connectSignalsSlots()

    def gIds(self):
        return self._gIds

    def setData(self, gIds, sources):
        self._gIds = gIds
        self._sources = sources
        self._load()

    def disableEdit(self):
        self._ui.dialogContent.setEnabled(False)
        self._ui.ok.hide()
        self._ui.cancel.setText(self.tr('Close'))
        self._editable = False

    def done(self, result):
        for actor in self._actors:
            self._renderingView.removeActor(actor)

        self._renderingView.refresh()

        super().done(result)

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            db = app.db.checkout()

            if len(self._gIds) == 1:
                name = self._ui.name.text()

                if name in RESERVED_NAMES:
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'), self.tr('"{0}" is an invalid geometry name.').format(name))
                    return

                if app.db.getElements('geometry', lambda i, e: e['name'] == name and i != self._gIds[0]):
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'), self.tr('geometry {0} already exists.').format(name))
                    return

                db.setValue(f'geometry/{self._gIds[0]}/name', name)

            for gId in self._gIds:
                element = db.checkout(f'geometry/{gId}')

                cfdType = self._typeRadios.checkedData()
                element.setValue('cfdType', cfdType)
                element.setValue('nonConformal', self._ui.nonConformal.isChecked())
                element.setValue('interRegion', self._ui.interRegion.isChecked())

                if cfdType != CFDType.INTERFACE.value:
                    element.setValue('slaveLayerGroup', None)
                    if cfdType != CFDType.BOUNDARY.value:
                        element.setValue('layerGroup', None)

                db.commit(element)

            if self._transformed:
                for gId, polyData in self._sources.items():
                    surface = app.db.getElement('geometry', gId)
                    db.updateGeometryPolyData(surface.value('path'), polyData)

            app.db.commit(db)

            super().accept()
        except ValidationError as e:
            await AsyncMessageBox().information(self, self.tr("Input Error"), e.toMessage())

    def _connectSignalsSlots(self):
        self._typeRadios.dataChecked.connect(self._onTypeChanged)
        self._transformWidget.transformed.connect(self._onTransformed)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self.close)

    def _load(self):
        surfaces = app.db.getElements('geometry', lambda i, e: i in self._gIds)

        first = surfaces[self._gIds[0]]
        if len(surfaces) > 1:
            self._ui.nameSetting.hide()
            self._transformWidget.hide()
        else:
            self._ui.name.setText(first.value('name'))
            if first.value('volume') is None and self._editable:
                self._displayPreview()
                self._transformWidget.setMeshes(self._sources)
            else:
                self._transformWidget.hide()

        cfdType = CFDType(first.value('cfdType'))
        nonConformal = None
        interRegion = None
        self._typeRadios.setCheckedData(cfdType)
        if cfdType == CFDType.INTERFACE:
            nonConformal = first.value('nonConformal')
            interRegion = first.value('interRegion')
            self._ui.nonConformal.setChecked(nonConformal)
            self._ui.interRegion.setChecked(interRegion)

        for gId, s in surfaces.items():
            if cfdType.value != s.value('cfdType'):
                self._typeRadios.setCheckedData(CFDType.BOUNDARY)
                break

            if (cfdType == CFDType.INTERFACE
                    and (nonConformal != s.value('nonConformal') or interRegion != s.value('interRegion'))):
                self._typeRadios.setCheckedData(CFDType.BOUNDARY)
                break

        self._onTypeChanged(self._typeRadios.checkedData())

    def _onTransformed(self):
        self._transformed = True
        self._sources = self._transformWidget.meshes()
        self._displayPreview()

    def _onTypeChanged(self, value):
        self._ui.interfaceType.setEnabled(value == CFDType.INTERFACE)

    def _displayPreview(self):
        for actor in self._actors:
            self._renderingView.removeActor(actor)

        self._actors.clear()

        for polyData in self._sources.values():
            actor = polyDataToActor(polyData)
            actor.GetProperty().SetRepresentationToSurface()
            actor.GetProperty().EdgeVisibilityOn()
            actor.GetProperty().SetLineWidth(1.0)
            actor.GetProperty().SetDiffuse(0.6)
            actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('burlywood'))
            actor.GetProperty().SetLineWidth(2)
            self._actors.append(actor)
            self._renderingView.addActor(actor)

        self._renderingView.refresh()
