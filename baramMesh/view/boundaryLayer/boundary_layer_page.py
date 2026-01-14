#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.exception import CanceledException
from libbaram.process import ProcessError
from libbaram.simple_db.simple_schema import ValidationError

from widgets.async_message_box import AsyncMessageBox
from widgets.list_table import ListItemWithButtons

from baramMesh.app import app
from baramMesh.db.configurations import defaultsDB
from baramMesh.openfoam.utility.snappy_hex_mesh import snappyHexMesh, BOUNDARY_LAYER_OUTPUT_TIME
from baramMesh.view.step_page import StepPage
from .boundary_setting_dialog import BoundarySettingDialog


class BoundaryLayerPage(StepPage):
    OUTPUT_TIME = BOUNDARY_LAYER_OUTPUT_TIME

    def __init__(self, ui):
        super().__init__(ui, ui.boundaryLayerPage)

        self._ui = ui
        self._dialog = None
        self._db = None
        self._cm = None

        ui.boundaryLayerConfigurationsHeader.setContents(ui.boundaryLayerConfigurations)
        ui.boundaryLayerConfigurations.setBackgroundColor()
        ui.boundaryLayerConfigurations.setHeaderWithWidth([0, 0, 16, 16])

        ui.boundaryLayerAdvancedConfigurationHeader.setContents(ui.boundaryLayerAdvancedConfiguration)

        ui.boundaryLayerCancel.hide()

        self._connectSignalsSlots()

    async def show(self, isCurrentStep, batchRunning):
        self.load()
        self.updateWorkingStatus()

        self._ui.boundaryLayerApply.setEnabled(isCurrentStep and not batchRunning)

    async def save(self):
        try:
            addLayer = self._db.checkout('addLayers')

            addLayer.setValue('nGrow', self._ui.nGrow.text(), self.tr('Number of Grow'))
            addLayer.setValue('featureAngle', self._ui.featureAngleThreshold.text(), self.tr('Feature Angle Threshold'))
            addLayer.setValue('maxFaceThicknessRatio', self._ui.maxFaceThicknessRatio.text(),
                              self.tr('Max. Thickness Ratio'))
            addLayer.setValue('nSmoothSurfaceNormals', self._ui.nSmoothSurfaceNormals.text(),
                              self.tr('Number of Iterations'))
            addLayer.setValue('nSmoothThickness', self._ui.nSmoothThickness.text(), self.tr('Smooth Layer Thickness'))
            addLayer.setValue('minMedialAxisAngle', self._ui.minMedialAxisAngle.text(), self.tr('Min. Axis Angle'))
            addLayer.setValue('maxThicknessToMedialRatio', self._ui.maxThicknessToMedialRatio.text(),
                              self.tr('Max. Thickness Ratio'))
            addLayer.setValue('nSmoothNormals', self._ui.nSmoothNormals.text(), self.tr('Number of Smoothing Iter.'))
            addLayer.setValue('nRelaxIter', self._ui.nRelaxIter.text(), self.tr('Max. Snapping Relaxation Iter.'))
            addLayer.setValue('nBufferCellsNoExtrude', self._ui.nBufferCellsNoExtrude.text(),
                              self.tr('Num. of Buffer Cells'))
            addLayer.setValue('nLayerIter', self._ui.nLayerIter.text(), self.tr('Max. Layer Addition Iter.'))
            addLayer.setValue('nRelaxedIter', self._ui.nRelaxedIter.text(), self.tr('Max. Iter. Before Relax'))

            self._db.commit(addLayer)

            app.db.commit(self._db)
            self._db = app.db.checkout()

            return True
        except ValidationError as e:
            await AsyncMessageBox().information(self._widget, self.tr("Input Error"), e.toMessage())

            return False

    def load(self):
        self._db = app.db.checkout()

        if self._loaded:
            return

        self._ui.boundaryLayerConfigurations.clear()

        groups = set()
        for gId, geometry in self._db.getElements('geometry').items():
            groups.add(geometry.value('layerGroup'))
            groups.add(geometry.value('slaveLayerGroup'))
        if None in groups:
            groups.remove(None)

        for groupId, element in self._db.getElements('addLayers/layers').items():
            if groupId in groups:
                self._addConfigurationItem(groupId, element.value('groupName'), element.value('nSurfaceLayers'))
            else:
                self._db.removeElement('addLayers/layers', groupId)

        self._setConfigurastions(self._db.getElement('addLayers'))

        self._loaded = True

    async def runInBatchMode(self):
        if not await self.save():
            return False

        self._ui.boundaryLayerApply.setEnabled(False)

        return await self._run()

    def _connectSignalsSlots(self):
        self._ui.loadBoundaryLayerDefaults.clicked.connect(self._loadDefaults)
        self._ui.boundaryLayerConfigurationsAdd.clicked.connect(lambda: self._openLayerEditDialog())
        # self._ui.layers.itemDoubleClicked.connect(self._openLayerEditDialog)
        self._ui.boundaryLayerApply.clicked.connect(self._apply)
        self._ui.boundaryLayerCancel.clicked.connect(snappyHexMesh.cancel)
        self._ui.boundaryLayerReset.clicked.connect(self._reset)

    @qasync.asyncSlot()
    async def _loadDefaults(self):
        if await AsyncMessageBox().confirm(
                self._widget, self.tr('Reset Settings'),
                self.tr('Would you like to reset all Boundary Layer settings to default,excluding the Layer Groups?')):
            self._setConfigurastions(defaultsDB.getElement('addLayers'))

    def _setConfigurastions(self, addLayer):
        self._ui.nGrow.setText(addLayer.value('nGrow'))
        self._ui.featureAngleThreshold.setText(addLayer.value('featureAngle'))
        self._ui.maxFaceThicknessRatio.setText(addLayer.value('maxFaceThicknessRatio'))
        self._ui.nSmoothSurfaceNormals.setText(addLayer.value('nSmoothSurfaceNormals'))
        self._ui.nSmoothThickness.setText(addLayer.value('nSmoothThickness'))
        self._ui.minMedialAxisAngle.setText(addLayer.value('minMedialAxisAngle'))
        self._ui.maxThicknessToMedialRatio.setText(addLayer.value('maxThicknessToMedialRatio'))
        self._ui.nSmoothNormals.setText(addLayer.value('nSmoothNormals'))
        self._ui.nRelaxIter.setText(addLayer.value('nRelaxIter'))
        self._ui.nBufferCellsNoExtrude.setText(addLayer.value('nBufferCellsNoExtrude'))
        self._ui.nLayerIter.setText(addLayer.value('nLayerIter'))
        self._ui.nRelaxedIter.setText(addLayer.value('nRelaxedIter'))

    def _openLayerEditDialog(self, groupId=None):
        self._dialog = BoundarySettingDialog(self._widget, self._db, groupId)
        if self._locked:
            self._dialog.disableEdit()
        else:
            self._dialog.accepted.connect(self._updateLayerConfiguration)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _apply(self):
        if not await self.save():
            return

        self._ui.boundaryLayerApply.hide()
        self._ui.boundaryLayerCancel.show()
        snappyHexMesh.snappyStarted.emit()

        app.consoleView.clear()

        if await self._run():
            self.stepCompleted.emit()

            await AsyncMessageBox().information(self._widget, self.tr('Complete'),
                                                self.tr('Boundary layers are applied.'))

        snappyHexMesh.snappyStopped.emit()
        self._enableEdit()
        self._ui.boundaryLayerCancel.hide()

        self.updateWorkingStatus()

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()
        self._ui.boundaryLayerApply.setEnabled(True)
        self.stepReset.emit()

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

        self._db.updateElements('geometry', 'layerGroup', None, lambda i, e: e['layerGroup'] == groupId)
        self._db.updateElements('geometry', 'slaveLayerGroup', None, lambda i, e: e['slaveLayerGroup'] == groupId)

        self._ui.boundaryLayerConfigurations.removeItem(groupId)

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.boundaryLayerApply.hide()
            self._ui.boundaryLayerReset.show()
        else:
            self._ui.boundaryLayerApply.show()
            self._ui.boundaryLayerApply.setEnabled(True)
            self._ui.boundaryLayerReset.hide()

    def _enableStep(self):
        self._enableEdit()
        self._ui.boundaryLayerButtons.setEnabled(True)

    def _disableStep(self):
        self._disableEdit()
        self._ui.boundaryLayerButtons.setEnabled(False)

    def _enableEdit(self):
        self._ui.loadBoundaryLayerDefaults.setEnabled(True)
        self._ui.boundaryLayerConfigurationsAdd.setEnabled(True)
        self._ui.boundaryLayerConfigurations.enableEdit()
        self._ui.boundaryLayerAdvancedConfiguration.setEnabled(True)

    def _disableEdit(self):
        self._ui.loadBoundaryLayerDefaults.setEnabled(False)
        self._ui.boundaryLayerConfigurationsAdd.setEnabled(False)
        self._ui.boundaryLayerConfigurations.disableEdit()
        self._ui.boundaryLayerAdvancedConfiguration.setEnabled(False)

    @qasync.asyncSlot()
    async def _run(self):
        self._disableEdit()

        result = False
        try:
            await snappyHexMesh.addLayers()
            result = True
        except ProcessError as exc:
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Failed to apply boundary layers [') + str(exc.returncode) + ']')
        except CanceledException:
            await AsyncMessageBox().information(self._widget, self.tr('Canceled'),
                                                self.tr('Boundary layers application has been canceled.'))
        except Exception as e:
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Failed to apply boundary layers:') + str(e))

        if not result:
            self.clearResult()

        return result
