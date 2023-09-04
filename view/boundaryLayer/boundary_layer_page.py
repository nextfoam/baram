#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio

import qasync
from PySide6.QtWidgets import QMessageBox

from app import app
from db.simple_schema import DBError
from openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from libbaram.run import runUtility
from libbaram.process import Processor, ProcessError
from view.step_page import StepPage
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from view.widgets.list_table import ListItemWithButtons
from .boundary_setting_dialog import BoundarySettingDialog
from .boundary_layer_advanced_dialog import BoundaryLayerAdvancedDialog


class BoundaryLayerPage(StepPage):
    OUTPUT_TIME = 3

    def __init__(self, ui):
        super().__init__(ui, ui.boundaryLayerPage)

        self._ui = ui

        self._dialog = None
        self._loaded = False

        self._db = None

        ui.boundaryLayerConfigurationsHeader.setContents(ui.boundaryLayerConfigurations)
        ui.boundaryLayerConfigurations.setHeaderWithWidth([0, 0, 16, 16])

        self._connectSignalsSlots()

    def open(self):
        self._load()

    def selected(self):
        if not self._loaded:
            self._load()

        self._updateControlButtons()
        self._updateMesh()

    def save(self):
        try:
            addLayer = app.db.checkout('addLayers')

            addLayer.setValue('nGrow', self._ui.nGrow.text(), self.tr('Number of Grow'))
            addLayer.setValue('maxFaceThicknessRatio', self._ui.maxFaceThicknessRatio.text(),
                              self.tr('Max. Thickness Ratio'))
            addLayer.setValue('nSmoothSurfaceNormals', self._ui.nSmoothSurfaceNormals.text(),
                              self.tr('Number of Iterations'))
            addLayer.setValue('nSmoothThickness', self._ui.nSmoothThickness.text(), self.tr('Smooth Layer Thickness'))
            addLayer.setValue('minMedialAxisAngle', self._ui.minMedialAxisAngle.text(), self.tr('Min. Axis Angle'))
            addLayer.setValue('maxThicknessToMedialRatio', self._ui.maxThicknessToMedialRatio.text(),
                              self.tr('Max. Thickness Ratio'))
            addLayer.setValue('nSmoothNormals', self._ui.nSmoothNormals.text(), self.tr('Number of Smoothing Iter.'))
            addLayer.setValue('slipFeatureAngle', self._ui.slipFeatureAngle.text(), self.tr('Slip Feature Angle'))
            addLayer.setValue('nRelaxIter', self._ui.nRelaxIter.text(), self.tr('Max. Snapping Relaxation Iter.'))
            addLayer.setValue('nBufferCellsNoExtrude', self._ui.nBufferCellsNoExtrude.text(),
                              self.tr('Num. of Buffer Cells'))
            addLayer.setValue('nLayerIter', self._ui.nLayerIter.text(), self.tr('Max. Layer Addition Iter.'))
            addLayer.setValue('nRelaxedIter', self._ui.nRelaxedIter.text(), self.tr('Max. Iter. Before Relax'))

            self._db.commit(addLayer)
            app.db.commit(self._db)

            self._db = app.db.checkout()

            return True
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

            return False

    def _connectSignalsSlots(self):
        self._ui.boundaryLayerConfigurationsAdd.clicked.connect(lambda: self._openLayerEditDialog())
        # self._ui.layers.itemDoubleClicked.connect(self._openLayerEditDialog)
        self._ui.boundaryLayerApply.clicked.connect(self._apply)
        self._ui.boundaryLayerReset.clicked.connect(self._reset)

    def _load(self):
        self._db = app.db.checkout()

        self._ui.boundaryLayerConfigurations.clear()

        groups = set()
        for gId, geometry in app.window.geometryManager.geometries().items():
            if group := geometry['layerGroup']:
                groups.add(group)

        for groupId, element in self._db.getElements('addLayers/layers').items():
            if groupId in groups:
                self._addConfigurationItem(groupId, element['groupName'], element['nSurfaceLayers'])
            else:
                self._db.removeElement('addLayers/layers', groupId)

        addLayer = app.db.checkout('addLayers')

        self._ui.nGrow.setText(addLayer.getValue('nGrow'))
        self._ui.maxFaceThicknessRatio.setText(addLayer.getValue('maxFaceThicknessRatio'))
        self._ui.nSmoothSurfaceNormals.setText(addLayer.getValue('nSmoothSurfaceNormals'))
        self._ui.nSmoothThickness.setText(addLayer.getValue('nSmoothThickness'))
        self._ui.minMedialAxisAngle.setText(addLayer.getValue('minMedialAxisAngle'))
        self._ui.maxThicknessToMedialRatio.setText(addLayer.getValue('maxThicknessToMedialRatio'))
        self._ui.nSmoothNormals.setText(addLayer.getValue('nSmoothNormals'))
        self._ui.slipFeatureAngle.setText(addLayer.getValue('slipFeatureAngle'))
        self._ui.nRelaxIter.setText(addLayer.getValue('nRelaxIter'))
        self._ui.nBufferCellsNoExtrude.setText(addLayer.getValue('nBufferCellsNoExtrude'))
        self._ui.nLayerIter.setText(addLayer.getValue('nLayerIter'))
        self._ui.nRelaxedIter.setText(addLayer.getValue('nRelaxedIter'))

        self._loaded = True
        self._updateControlButtons()

    def _openLayerEditDialog(self, groupId=None):
        self._dialog = BoundarySettingDialog(self._widget, self._db, groupId)
        self._dialog.accepted.connect(self._updateLayerConfiguration)
        self._dialog.open()

    def _advancedConfigure(self):
        self._advancedDialog = BoundaryLayerAdvancedDialog(self._widget)
        self._advancedDialog.open()

    @qasync.asyncSlot()
    async def _apply(self):
        try:
            self.lock()

            if not self.save():
                return

            console = app.consoleView
            console.clear()

            if self._ui.boundaryLayerConfigurations.count():
                progressDialog = ProgressDialogSimple(self._widget, self.tr('Boundary Layers Applying'))
                progressDialog.setLabelText(self.tr('Updating Configurations'))
                progressDialog.open()

                SnappyHexMeshDict(addLayers=True).build().write()
                # TopoSetDict().build().write()

                progressDialog.close()

                proc = await runUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(),
                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                processor = Processor(proc)
                processor.outputLogged.connect(console.append)
                processor.errorLogged.connect(console.appendError)
                await processor.run()
                #
                # proc = await runUtility('toposet', cwd=app.fileSystem.caseRoot(),
                #                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                # processor = Processor(proc)
                # processor.outputLogged.connect(console.append)
                # processor.errorLogged.connect(console.appendError)
                # await processor.run()
            else:
                app.fileSystem.timePath(self.OUTPUT_TIME).mkdir()

            await app.window.meshManager.load(self.OUTPUT_TIME)
            self._updateControlButtons()
        except ProcessError as e:
            self.clearResult()
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Boundary Layers Applying Failed. [') + str(e.returncode) + ']')
        finally:
            self.unlock()

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()

    def _updateLayerConfiguration(self):
        element = self._dialog.dbElement()
        if self._dialog.isCreationMode():
            self._addConfigurationItem(self._dialog.groupId(), element.getValue('groupName'),
                                       element.getValue('nSurfaceLayers'))
        else:
            self._ui.boundaryLayerConfigurations.item(self._dialog.groupId()).update(
                [element.getValue('groupName'), element.getValue('nSurfaceLayers')])

    def _addConfigurationItem(self, groupId, name, layers):
        item = ListItemWithButtons(groupId, [name, layers])
        item.editClicked.connect(lambda: self._openLayerEditDialog(groupId))
        item.removeClicked.connect(lambda: self._removeLayerConfiguration(groupId))
        self._ui.boundaryLayerConfigurations.addItem(item)

    def _removeLayerConfiguration(self, groupId):
        self._db.removeElement('addLayers/layers', groupId)
        gIds = self._db.updateElements('geometry', 'layerGroup', None, lambda i, e: e['layerGroup'] == groupId)
        for gId in gIds:
            app.window.geometryManager.updateGeometryPropety(gId, 'layerGroup', None)

        self._ui.boundaryLayerConfigurations.removeItem(groupId)

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.boundaryLayerApply.hide()
            self._ui.boundaryLayerReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.boundaryLayerApply.show()
            self._ui.boundaryLayerReset.hide()
            self._setNextStepEnabled(False)
