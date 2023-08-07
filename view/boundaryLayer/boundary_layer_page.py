#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio

import qasync
from PySide6.QtWidgets import QMessageBox

from app import app
from db.configurations_schema import GeometryType, CFDType
from db.simple_schema import DBError
from openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from libbaram.run import runUtility
from libbaram.process import Processor
from view.step_page import StepPage
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from .thickness_form import ThicknessForm
from .layer_item import LayerItem
from .boundary_setting_dialog import BoundarySettingDialog
from .boundary_layer_advanced_dialog import BoundaryLayerAdvancedDialog


class BoundaryLayerPage(StepPage):
    OUTPUT_TIME = 3

    def __init__(self, ui):
        super().__init__(ui, ui.boundaryLayerPage)

        self._ui = ui
        self._thicknessForm = ThicknessForm(ui)

        self._layers = {}

        self._dialog = None
        self._advancedDialog = None

        self._loaded = False

        self._connectSignalsSlots()

    def lock(self):
        self._widget.setEnabled(False)

    def unlock(self):
        self._widget.setEnabled(True)

    def open(self):
        self._load()

    def selected(self):
        if not self._loaded:
            self._load()

    def save(self):
        try:
            db = app.db.checkout('addLayers')
            self._thicknessForm.save(db)
            app.db.commit(db)

            return True
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

            return False

    def _connectSignalsSlots(self):
        self._ui.layers.itemDoubleClicked.connect(self._openLayerEditDialog)
        self._ui.boundaryLayerAdvanced.clicked.connect(self._advancedConfigure)
        self._ui.boundaryLayerApply.clicked.connect(self._apply)
        self._ui.boundaryLayerReset.clicked.connect(self._reset)

    def _load(self):
        db = app.db.checkout('addLayers')
        self._thicknessForm.setData(db)

        self._ui.layers.clear()
        layers = db.getElements('layers', None, ['useLocalSetting', 'nSurfaceLayers'])
        for gID, geometry in app.window.geometryManager.geometries().items():
            if geometry['cfdType'] != CFDType.NONE.value and geometry['gType'] == GeometryType.SURFACE.value:
                if gID in layers:
                    nSurfaceLayers = layers.pop(gID)['nSurfaceLayers']
                else:
                    _, layer = db.addNewElement('layers', gID)
                    nSurfaceLayers = layer.getValue('nSurfaceLayers')

                item = LayerItem(gID, geometry['name'], nSurfaceLayers)
                item.addTo(self._ui.layers)
                self._layers[gID] = item

        db.removeElements('layers', layers)
        app.db.commit(db)

        self._loaded = True
        self._checkAppylied()

    def _openLayerEditDialog(self, item):
        self._dialog = BoundarySettingDialog(self._widget, str(item.type()), self._thicknessForm)
        self._dialog.accepted.connect(self._updateLayer)
        self._dialog.open()

    def _advancedConfigure(self):
        self._advancedDialog = BoundaryLayerAdvancedDialog(self._widget)
        self._advancedDialog.open()

    @qasync.asyncSlot()
    async def _apply(self):
        try:
            self.lock()

            progressDialog = ProgressDialogSimple(self._widget, self.tr('Boundary Layers Applying'))
            progressDialog.setLabelText(self.tr('Updating Configurations'))
            progressDialog.open()

            if not self.save():
                self.unlock()
                progressDialog.close()
                return

            SnappyHexMeshDict(addLayers=True).build().write()

            progressDialog.close()

            console = app.consoleView
            console.clear()
            proc = await runUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(),
                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            processor = Processor(proc)
            processor.outputLogged.connect(console.append)
            processor.errorLogged.connect(console.appendError)
            if returncode := await processor.run():
                progressDialog.finish(self.tr('Boumdary Layers Applying Failed. [') + str(returncode) + ']')
                self.unlock()
                return

            progressDialog = ProgressDialogSimple(self._widget, self.tr('Loading Mesh'), False)
            progressDialog.setLabelText(self.tr('Loading Mesh'))
            progressDialog.open()

            meshManager = app.window.meshManager
            meshManager.clear()
            meshManager.progress.connect(progressDialog.setLabelText)
            await meshManager.load()

            progressDialog.close()
        except Exception as ex:
            QMessageBox.information(self._widget, self.tr("Boumdary Layers Applying Failed."), str(ex))
        finally:
            self.unlock()
            self._checkAppylied()

    def _reset(self):
        self.clearResult()
        self._checkAppylied()

    def _updateLayer(self):
        gID = self._dialog.gID()
        self._layers[gID].setLayers(app.db.getValue(f'addLayers/layers/{gID}/nSurfaceLayers'))

    def _checkAppylied(self):
        if self.isNextStepAvailable():
            self._ui.boundaryLayerApply.hide()
            self._ui.boundaryLayerReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.boundaryLayerApply.show()
            self._ui.boundaryLayerReset.hide()
            self._setNextStepEnabled(False)
