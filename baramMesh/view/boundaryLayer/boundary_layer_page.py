#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.exception import CanceledException
from libbaram.run import RunParallelUtility
from libbaram.process import ProcessError
from libbaram.simple_db.simple_schema import DBError
from libbaram.utils import copyOrLink

from widgets.async_message_box import AsyncMessageBox
from widgets.list_table import ListItemWithButtons
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType
from baramMesh.openfoam.system.create_patch_dict import CreatePatchDict
from baramMesh.openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from baramMesh.view.step_page import StepPage

from .boundary_setting_dialog import BoundarySettingDialog
from .restore_cyclic_patch_names import RestoreCyclicPatchNames


class BoundaryLayerPage(StepPage):
    OUTPUT_TIME = 3

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

        self._connectSignalsSlots()

    def open(self):
        self._load()

    async def selected(self):
        if not self._loaded:
            self._load()

        self._updateControlButtons()
        self._updateMesh()

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
        except DBError as e:
            await AsyncMessageBox().information(self._widget, self.tr("Input Error"), e.toMessage())

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

        addLayer = self._db.getElement('addLayers')

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

        self._loaded = True
        self._updateControlButtons()

    def _openLayerEditDialog(self, groupId=None):
        self._dialog = BoundarySettingDialog(self._widget, self._db, groupId)
        if self._locked:
            self._dialog.disableEdit()
        else:
            self._dialog.accepted.connect(self._updateLayerConfiguration)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _apply(self):
        if self._cm:
            self._cm.cancel()
            return

        buttonText = self._ui.boundaryLayerApply.text()
        try:
            if not await self.save():
                return

            self._disableEdit()
            self._disableControlsForRunning()
            self._ui.boundaryLayerApply.setText(self.tr('Cancel'))

            console = app.consoleView
            console.clear()

            #
            #  Add Boundary Layers
            #

            boundaryLayersAdded = False

            if self._ui.boundaryLayerConfigurations.count():
                progressDialog = ProgressDialog(self._widget, self.tr('Boundary Layers Applying'))
                progressDialog.setLabelText(self.tr('Updating Configurations'))
                progressDialog.open()

                SnappyHexMeshDict(addLayers=True).build().write()

                progressDialog.close()

                self._cm = RunParallelUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                rc = await self._cm.wait()
                if rc != 0:
                    raise ProcessError(rc)

                boundaryLayersAdded = True

            else:
                self.createOutputPath()

            #
            #  Reorder faces in conformal interfaces
            #  (Faces in cyclic boundary pair should match in order)
            #

            NumberOfConformalInterfaces = app.db.elementCount(
                'geometry', lambda i, e: e['cfdType'] == CFDType.INTERFACE.value and not e['interRegion'] and not e['nonConformal'])

            if NumberOfConformalInterfaces > 0:
                prefix = 'NFBRM_'
                CreatePatchDict(prefix).build().write()
                self._cm = RunParallelUtility('createPatch', '-allRegions', '-overwrite', '-case', app.fileSystem.caseRoot(),
                                              cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                await self._cm.wait()

                rpn = RestoreCyclicPatchNames(prefix, str(self.OUTPUT_TIME))
                rpn.restore()

            if boundaryLayersAdded:
                self._cm = RunParallelUtility('checkMesh', '-allRegions', '-writeFields', '(cellAspectRatio cellVolume nonOrthoAngle skewness)', '-time', str(self.OUTPUT_TIME), '-case', app.fileSystem.caseRoot(),
                                              cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                await self._cm.wait()
            else:  # Mesh Quality information should be in this time folder
                nProcFolders = app.fileSystem.numberOfProcessorFolders()
                if nProcFolders == 0:
                    source = app.fileSystem.timePath(self.OUTPUT_TIME-1)
                    target = app.fileSystem.timePath(self.OUTPUT_TIME)
                    copyOrLink(source / 'cellAspectRatio', target / 'cellAspectRatio')
                    copyOrLink(source / 'cellVolume', target / 'cellVolume')
                    copyOrLink(source / 'nonOrthoAngle', target / 'nonOrthoAngle')
                    copyOrLink(source / 'skewness', target / 'skewness')
                else:
                    for processorNo in range(nProcFolders):
                        source = app.fileSystem.timePath(self.OUTPUT_TIME-1, processorNo)
                        target = app.fileSystem.timePath(self.OUTPUT_TIME, processorNo)
                        copyOrLink(source / 'cellAspectRatio', target / 'cellAspectRatio')
                        copyOrLink(source / 'cellVolume', target / 'cellVolume')
                        copyOrLink(source / 'nonOrthoAngle', target / 'nonOrthoAngle')
                        copyOrLink(source / 'skewness', target / 'skewness')

            await app.window.meshManager.load(self.OUTPUT_TIME)
            self._updateControlButtons()

            await AsyncMessageBox().information(self._widget, self.tr('Complete'),
                                                self.tr('Boundary layers are applied.'))
        except ProcessError as exc:
            self.clearResult()
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Failed to apply boundary layers. [') + str(exc.returncode) + ']')
        except CanceledException:
            self.clearResult()
            await AsyncMessageBox().information(self._widget, self.tr('Canceled'),
                                                self.tr('Boundary layers application has been canceled.'))
        finally:
            self._enableEdit()
            self._enableControlsForSettings()
            self._ui.boundaryLayerApply.setText(buttonText)
            self._cm = None

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

        self._db.updateElements('geometry', 'layerGroup', None, lambda i, e: e['layerGroup'] == groupId)
        self._db.updateElements('geometry', 'slaveLayerGroup', None, lambda i, e: e['slaveLayerGroup'] == groupId)

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

    def _enableStep(self):
        self._enableEdit()
        self._ui.boundaryLayerButtons.setEnabled(True)

    def _disableStep(self):
        self._disableEdit()
        self._ui.boundaryLayerButtons.setEnabled(False)

    def _enableEdit(self):
        self._ui.boundaryLayerConfigurationsAdd.setEnabled(True)
        self._ui.boundaryLayerConfigurations.enableEdit()
        self._ui.boundaryLayerAdvancedConfiguration.setEnabled(True)

    def _disableEdit(self):
        self._ui.boundaryLayerConfigurationsAdd.setEnabled(False)
        self._ui.boundaryLayerConfigurations.disableEdit()
        self._ui.boundaryLayerAdvancedConfiguration.setEnabled(False)
