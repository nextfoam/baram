#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from libbaram.exception import CanceledException
from libbaram.process import ProcessError
from libbaram.run import RunParallelUtility
from libbaram.simple_db.simple_schema import DBError
from widgets.async_message_box import AsyncMessageBox
from widgets.enum_button_group import EnumButtonGroup
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType, FeatureSnapType, BufferLayerPointSmoothingMethod, GeometryType
from baramMesh.openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from baramMesh.openfoam.system.topo_set_dict import TopoSetDict
from baramMesh.view.step_page import StepPage


class SnapPage(StepPage):
    OUTPUT_TIME = 2

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

        self._connectSignalsSlots()

    async def selected(self):
        if not self._loaded:
            self._load()

        self.updateMesh()

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
        except DBError as e:
            await AsyncMessageBox().information(self._widget, self.tr('Input Error'), e.toMessage())

            return False

    def _connectSignalsSlots(self):
        self._ui.snap.clicked.connect(self._snap)
        self._ui.snapReset.clicked.connect(self._reset)
        self._ui.featureSnapType.currentDataChanged.connect(self._featureSnapTypeChanged)
        self._smoothingMethod.dataChecked.connect(self._smootingMethodChanged)
        self._ui.bufferLayerSurfacesSelect.clicked.connect(self._selectSurfaces)

    def _load(self):
        dbElement = app.db.checkout('snap')
        self._ui.smoothingForSurface.setText(dbElement.getValue('nSmoothPatch'))
        self._ui.smoothingForInternal.setText(dbElement.getValue('nSmoothInternal'))
        self._ui.meshDisplacementRelaxation.setText(dbElement.getValue('nSolveIter'))
        self._ui.globalSnappingRelaxation.setText(dbElement.getValue('nRelaxIter'))
        self._ui.featureSnappingRelaxation.setText(dbElement.getValue('nFeatureSnapIter'))
        self._ui.featureSnapType.setCurrentData(FeatureSnapType(dbElement.getValue('featureSnapType')))
        self._ui.multiSurfaceFeatureSnap.setChecked(dbElement.getValue('multiRegionFeatureSnap'))
        self._ui.tolerance.setText(dbElement.getValue('tolerance'))
        self._ui.concaveAngle.setText(dbElement.getValue('concaveAngle'))
        self._ui.minAreaRatio.setText(dbElement.getValue('minAreaRatio'))

        bufferLayer = dbElement.getElement('bufferLayer')
        self._ui.bufferLayer.setChecked(not bufferLayer.value('disabled'))
        self._smoothingMethod.setCheckedData(bufferLayer.enum('pointSmoothingMethod'))
        self._ui.bufferLayerNumberOfPointSmootherIteration.setText(bufferLayer.value('numberOfPointSmoothingIteration'))
        self._ui.bufferLayerGETMeTransformationParameter.setText(bufferLayer.value('GETMeTransformationParameter'))

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

        self._updateControlButtons()

    @qasync.asyncSlot()
    async def _snap(self):
        if self._cm:
            self._cm.cancel()
            return

        buttonText = self._ui.snap.text()

        try:
            if not await self.save():
                return

            self._ui.snapContents.setEnabled(False)
            self._disableControlsForRunning()
            self._ui.snap.setText(self.tr('Cancel'))

            console = app.consoleView
            console.clear()

            parallel = app.project.parallelEnvironment()

            snapDict = SnappyHexMeshDict(snap=True).build()
            if app.db.elementCount('region') > 1:
                snapDict.write()
            else:
                snapDict.updateForCellZoneInterfacesSnap().write()

            self._cm = RunParallelUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(), parallel=parallel)
            self._cm.output.connect(console.append)
            self._cm.errorOutput.connect(console.appendError)
            await self._cm.start()
            rc = await self._cm.wait()
            if rc != 0:
                raise ProcessError(rc)

            if app.db.elementCount('region') > 1:
                TopoSetDict().build(TopoSetDict.Mode.CREATE_REGIONS).write()

                self._cm = RunParallelUtility('topoSet', cwd=app.fileSystem.caseRoot(), parallel=parallel)
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                rc = await self._cm.wait()
                if rc != 0:
                    raise ProcessError(rc)

                if app.db.elementCount('geometry', lambda i, e: e['cfdType'] == CFDType.CELL_ZONE.value):
                    snapDict.updateForCellZoneInterfacesSnap().removeBufferLayers().write()

                    self._cm = RunParallelUtility('snappyHexMesh', '-overwrite', cwd=app.fileSystem.caseRoot(), parallel=parallel)
                    self._cm.output.connect(console.append)
                    self._cm.errorOutput.connect(console.appendError)
                    await self._cm.start()
                    rc = await self._cm.wait()
                    if rc != 0:
                        raise ProcessError(rc)

            self._cm = RunParallelUtility('checkMesh', '-allRegions', '-writeFields', '(cellAspectRatio cellVolume nonOrthoAngle skewness)', '-time', str(self.OUTPUT_TIME), '-case', app.fileSystem.caseRoot(),
                                    cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
            self._cm.output.connect(console.append)
            self._cm.errorOutput.connect(console.appendError)
            await self._cm.start()
            await self._cm.wait()

            await app.window.meshManager.load(self.OUTPUT_TIME)
            self._updateControlButtons()

            await AsyncMessageBox().information(self._widget, self.tr('Complete'), self.tr('Snapping is completed.'))
        except ProcessError as e:
            self.clearResult()
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Snapping Failed. [') + str(e.returncode) + ']')
        except CanceledException:
            self.clearResult()
            await AsyncMessageBox().information(self._widget, self.tr('Canceled'),
                                                self.tr('Snapping has been canceled.'))
        finally:
            self._ui.snapContents.setEnabled(True)
            self._enableControlsForSettings()
            self._ui.snap.setText(buttonText)
            self._cm = None

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()

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
            self._setNextStepEnabled(True)
        else:
            self._ui.snap.show()
            self._ui.snapReset.hide()
            self._setNextStepEnabled(False)
