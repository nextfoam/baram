#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.exception import CanceledException
from libbaram.process import ProcessError
from libbaram.simple_db.simple_schema import ValidationError
from widgets.async_message_box import AsyncMessageBox
from widgets.enum_button_group import EnumButtonGroup
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem

from baramMesh.app import app
from baramMesh.db.configurations import defaultsDB
from baramMesh.db.configurations_schema import CFDType, FeatureSnapType, BufferLayerPointSmoothingMethod, GeometryType
from baramMesh.openfoam.utility.snappy_hex_mesh import snappyHexMesh, SNAP_OUTPUT_TIME
from baramMesh.view.step_page import StepPage


class SnapPage(StepPage):
    OUTPUT_TIME = SNAP_OUTPUT_TIME

    def __init__(self, ui):
        super().__init__(ui, ui.snapPage)

        self._cm = None

        self._smoothingMethod = EnumButtonGroup()

        self._dialog = None

        self._availableSurfaces = None
        self._surfaces = None
        self._oldSurfaces = None

        self._ui.featureSnapType.addEnumItems({
            FeatureSnapType.EXPLICIT: self.tr('explicit'),
            FeatureSnapType.IMPLICIT: self.tr('implicit')
        })

        self._smoothingMethod.addEnumButton(self._ui.bufferLayerLaplacian, BufferLayerPointSmoothingMethod.LAPLACIAN)
        self._smoothingMethod.addEnumButton(self._ui.bufferLayerGETMe, BufferLayerPointSmoothingMethod.GETME)

        self._ui.snapCancel.hide()

        self._connectSignalsSlots()

    async def show(self, isCurrentStep, batchRunning):
        self.load()
        self.updateWorkingStatus()

        self._ui.snap.setEnabled(isCurrentStep and not batchRunning)

    async def save(self):
        try:
            db = app.db.checkout()
            snap = db.checkout('snap')

            snap.setValue('nSmoothPatch', self._ui.smoothingForSurface.text(), self.tr('Smoothing for Surface'))
            snap.setValue('nSmoothInternal', self._ui.smoothingForInternal.text(), self.tr('Smoothing for Internal'))
            snap.setValue('nSolveIter', self._ui.meshDisplacementRelaxation.text(),
                        self.tr('Mesh Displacement Relaxation'))
            snap.setValue('nRelaxIter', self._ui.globalSnappingRelaxation.text(), self.tr('Global Snapping Relaxation'))
            snap.setValue('featureSnapType', self._ui.featureSnapType.currentData(), None)
            snap.setValue('nFeatureSnapIter', self._ui.featureSnappingRelaxation.text(),
                        self.tr('Feature Snapping Relaxation'))
            snap.setValue('multiRegionFeatureSnap', self._ui.multiSurfaceFeatureSnap.isChecked())
            snap.setValue('tolerance', self._ui.tolerance.text(), self.tr('Tolerance'))
            snap.setValue('concaveAngle', self._ui.concaveAngle.text(), self.tr('Concave Angle'))
            snap.setValue('minAreaRatio', self._ui.minAreaRatio.text(), self.tr('Min. Area Ratio'))

            if self._ui.bufferLayer.isChecked():
                if not self._surfaces:
                    await AsyncMessageBox().information(self._widget, self.tr('Input Error'),
                                                        self.tr('Select Surface(s) for Buffer Layer.'))

                    return False

                snap.setValue('bufferLayer/disabled', False)
                snap.setValue('bufferLayer/pointSmoothingMethod', self._smoothingMethod.checkedData())
                snap.setValue('bufferLayer/numberOfPointSmoothingIteration',
                            self._ui.bufferLayerNumberOfPointSmootherIteration.text(),
                            self.tr('Number of Point Smoothing Iteration'))
                snap.setValue('bufferLayer/GETMeTransformationParameter', self._ui.bufferLayerGETMeTransformationParameter.text(),
                            self.tr('GETMe Transformation parameter'))

                surfaces = {gid: False for gid in self._oldSurfaces}
                surfaces.update({gid: True for gid in self._surfaces})
                for gid, addBufferLayers in surfaces.items():
                    db.setValue(f'geometry/{gid}/addBufferLayers', addBufferLayers)
            else:
                snap.setValue('bufferLayer/disabled', True)

            db.commit(snap)
            app.db.commit(db)

            self._oldSurfaces = self._surfaces

            return True
        except ValidationError as e:
            await AsyncMessageBox().information(self._widget, self.tr('Input Error'), e.toMessage())

            return False

    def load(self):
        if self._loaded:
            return

        dbElement = app.db.checkout()

        self._setConfigurations(dbElement.getElement('snap'))

        self._availableSurfaces = []
        self._surfaces = []
        self._ui.bufferLayerSurfaces.clear()
        for gid, geometry in app.db.getElements('geometry').items():
            if geometry.enum('gType') == GeometryType.SURFACE:
                name = geometry.value('name')
                isInterface = geometry.enum('cfdType') == CFDType.INTERFACE

                self._availableSurfaces.append(SelectorItem(name, name, gid, not isInterface))

                if geometry.value('addBufferLayers') or isInterface:
                    self._ui.bufferLayerSurfaces.addItem(name)
                    self._surfaces.append(gid)

        self._oldSurfaces = self._surfaces

        self._loaded = True

    async def runInBatchMode(self):
        if not await self.save():
            return False

        self._ui.snap.setEnabled(False)

        return await self._run()

    def _connectSignalsSlots(self):
        self._ui.loadSnapDefaults.clicked.connect(self._loadDefaults)
        self._ui.snap.clicked.connect(self._snap)
        self._ui.snapCancel.clicked.connect(snappyHexMesh.cancel)
        self._ui.snapReset.clicked.connect(self._reset)
        self._ui.featureSnapType.currentDataChanged.connect(self._featureSnapTypeChanged)
        self._smoothingMethod.dataChecked.connect(self._smootingMethodChanged)
        self._ui.bufferLayerSurfacesSelect.clicked.connect(self._selectSurfaces)

    @qasync.asyncSlot()
    async def _loadDefaults(self):
        if await AsyncMessageBox().confirm(
                self._widget, self.tr('Reset Settings'),
                self.tr('Would you like to reset all Snap settings to default, excluding the Buffer Layer Surfaces?')):
            self._setConfigurations(defaultsDB.getElement('snap'))

    def _setConfigurations(self, snap):
        self._ui.smoothingForSurface.setText(snap.value('nSmoothPatch'))
        self._ui.smoothingForInternal.setText(snap.value('nSmoothInternal'))
        self._ui.meshDisplacementRelaxation.setText(snap.value('nSolveIter'))
        self._ui.globalSnappingRelaxation.setText(snap.value('nRelaxIter'))
        self._ui.featureSnappingRelaxation.setText(snap.value('nFeatureSnapIter'))
        self._ui.featureSnapType.setCurrentData(FeatureSnapType(snap.value('featureSnapType')))
        self._ui.multiSurfaceFeatureSnap.setChecked(snap.value('multiRegionFeatureSnap'))
        self._ui.tolerance.setText(snap.value('tolerance'))
        self._ui.concaveAngle.setText(snap.value('concaveAngle'))
        self._ui.minAreaRatio.setText(snap.value('minAreaRatio'))

        bufferLayer = snap.element('bufferLayer')
        self._ui.bufferLayer.setChecked(not bufferLayer.value('disabled'))
        self._smoothingMethod.setCheckedData(bufferLayer.enum('pointSmoothingMethod'))
        self._ui.bufferLayerNumberOfPointSmootherIteration.setText(bufferLayer.value('numberOfPointSmoothingIteration'))
        self._ui.bufferLayerGETMeTransformationParameter.setText(bufferLayer.value('GETMeTransformationParameter'))

    @qasync.asyncSlot()
    async def _snap(self):
        if not await self.save():
            return

        self._ui.snap.hide()
        self._ui.snapCancel.show()
        snappyHexMesh.snappyStarted.emit()

        app.consoleView.clear()

        if await self._run():
            self.stepCompleted.emit()

            await AsyncMessageBox().information(self._widget, self.tr('Complete'), self.tr('Snapping is completed.'))

        snappyHexMesh.snappyStopped.emit()
        self._enableEdit()
        self._ui.snapCancel.hide()

        self.updateWorkingStatus()

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()
        self._ui.snap.setEnabled(True)
        self.stepReset.emit()

    def _featureSnapTypeChanged(self, type_):
        self._ui.multiSurfaceFeatureSnap.setEnabled(type_ == FeatureSnapType.EXPLICIT)

    def _smootingMethodChanged(self, method):
        self._ui.bufferLayerGETMeTransformationParameter.setEnabled(method == BufferLayerPointSmoothingMethod.GETME)

    def _selectSurfaces(self):
        self._dialog = MultiSelectorDialog(self._widget, self.tr('Select Surfaces'),
                                           self._availableSurfaces, self._surfaces)
        self._dialog.itemsSelected.connect(self._setSurfaces)
        self._dialog.open()

    def _setSurfaces(self, items):
        self._surfaces = []
        self._ui.bufferLayerSurfaces.clear()
        for gId, name in items:
            self._surfaces.append(gId)
            self._ui.bufferLayerSurfaces.addItem(name)

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.snap.hide()
            self._ui.snapReset.show()
            print(self._locked)
        else:
            self._ui.snap.show()
            self._ui.snap.setEnabled(True)
            self._ui.snapReset.hide()

    def _enableStep(self):
        super()._enableStep()
        self._enableEdit()

    def _disableStep(self):
        super()._disableStep()
        self._disableEdit()

    def _enableEdit(self):
        self._ui.loadSnapDefaults.setEnabled(True)
        self._ui.snapContents.setEnabled(True)

    def _disableEdit(self):
        self._ui.loadSnapDefaults.setEnabled(False)
        self._ui.snapContents.setEnabled(False)

    @qasync.asyncSlot()
    async def _run(self):
        self._disableEdit()

        result = False
        try:
            await snappyHexMesh.snap()
            result = True
        except ProcessError as e:
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Snapping Failed [') + str(e.returncode) + ']')
        except CanceledException:
            await AsyncMessageBox().information(self._widget, self.tr('Canceled'),
                                                self.tr('Snapping has been canceled.'))
        except Exception as e:
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Snapping Failed:') + str(e))

        if not result:
            self.clearResult()

        return result
