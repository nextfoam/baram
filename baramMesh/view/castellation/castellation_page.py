#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import qasync
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QApplication
from vtkmodules.vtkCommonDataModel import vtkPlane
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkCleanPolyData, vtkFeatureEdges, vtkPolyDataPlaneCutter, \
    vtkTriangleFilter
from vtkmodules.vtkIOGeometry import vtkSTLWriter, vtkOBJWriter

from libbaram.exception import CanceledException
from libbaram.process import ProcessError
from libbaram.run import RunParallelUtility
from libbaram.simple_db.simple_schema import DBError
from widgets.async_message_box import AsyncMessageBox
from widgets.list_table import ListItemWithButtons
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType, Shape, CFDType
from baramMesh.openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from baramMesh.view.main_window.main_window_ui import Ui_MainWindow
from baramMesh.view.step_page import StepPage
from .surface_refinement_dialog import SurfaceRefinementDialog
from .volume_refinement_dialog import VolumeRefinementDialog


def Plane(ox, oy, oz, nx, ny, nz):
    plane = vtkPlane()
    plane.SetOrigin(ox, oy, oz)
    plane.SetNormal(nx, ny, nz)

    return plane


def _writeFeatureFile(path: Path, pd):
    edges = vtkFeatureEdges()
    edges.SetInputData(pd)
    edges.SetNonManifoldEdges(app.db.getValue('castellation/vtkNonManifoldEdges'))
    edges.SetBoundaryEdges(app.db.getValue('castellation/vtkBoundaryEdges'))
    edges.SetFeatureAngle(float(app.db.getValue('castellation/resolveFeatureAngle')))
    edges.Update()

    features = vtkAppendPolyData()
    features.AddInputData(edges.GetOutput())

    _, geometry = app.window.geometryManager.getBoundingHex6()
    if geometry is not None:  # boundingHex6 is configured
        x1, y1, z1 = geometry.vector('point1')
        x2, y2, z2 = geometry.vector('point2')

        planes = [
            Plane(x1, 0, 0, -1, 0, 0),
            Plane(x2, 0, 0, 1, 0, 0),
            Plane(0, y1, 0, 0, -1, 0),
            Plane(0, y2, 0, 0, 1, 0),
            Plane(0, 0, z1, 0, 0, -1),
            Plane(0, 0, z2, 0, 0, 1)
        ]

        # vtkTriangleFilter is used to convert "Triangle Strips" to Triangles
        tf = vtkTriangleFilter()
        tf.SetInputData(pd)
        tf.Update()

        # "cutter" should be created in the loop
        # because its pointer is handed over to vtkAppendPolyData
        for p in planes:
            cutter = vtkPolyDataPlaneCutter()
            cutter.SetInputData(tf.GetOutput())
            cutter.SetPlane(p)
            cutter.Update()

            if cutter.GetOutput().GetNumberOfCells() > 0:
                features.AddInputData(cutter.GetOutput())

    features.Update()

    writer = vtkOBJWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(features.GetOutput())
    writer.Write()


class CastellationPage(StepPage):
    OUTPUT_TIME = 1

    def __init__(self, ui: Ui_MainWindow):
        super().__init__(ui, ui.castellationPage)

        self._ui = ui
        self._db = None
        self._dialog = None
        self._cm = None

        ui.castellationConfigurationHeader.setContents(ui.castellationConfiguration)
        ui.castellationAdvancedHeader.setContents(ui.castellationAdvanced)
        ui.surfaceRefinementHeader.setContents(ui.surfaceRefinement)
        ui.volumeRefinementHeader.setContents(ui.volumeRefinement)

        ui.surfaceRefinement.setBackgroundColor()
        ui.volumeRefinement.setBackgroundColor()
        ui.surfaceRefinement.setHeaderWithWidth([0, 0, 0, 16, 16])
        ui.volumeRefinement.setHeaderWithWidth([0, 0, 16, 16])

        ui.nCellsBetweenLevels.setValidator(QIntValidator(1, 1000000))

        self._connectSignalsSlots()

    def open(self):
        self._load()

    async def selected(self):
        if not self._loaded:
            self._load()

        self._updateControlButtons()
        self.updateMesh()

    async def save(self):
        try:
            castellation = self._db.checkout('castellation')

            castellation.setValue('nCellsBetweenLevels', self._ui.nCellsBetweenLevels.text(),
                              self.tr('Number of Cells between Levels'))
            castellation.setValue('resolveFeatureAngle', self._ui.resolveFeatureAngle.text(),
                              self.tr('Feature Angle Threshold'))
            castellation.setValue('vtkNonManifoldEdges', self._ui.keepNonManifoldEdges.isChecked())
            castellation.setValue('vtkBoundaryEdges', self._ui.keepOpenEdges.isChecked())

            castellation.setValue('maxGlobalCells', self._ui.maxGlobalCells.text(), self.tr('Max. Global Cell Count'))
            castellation.setValue('maxLocalCells', self._ui.maxLocalCells.text(), self.tr('Max. Local Cell Count'))
            castellation.setValue('minRefinementCells', self._ui.minRefinementCells.text(),
                              self.tr('Min.Refinement Cell Count'))
            castellation.setValue('maxLoadUnbalance', self._ui.maxLoadUnbalance.text(), self.tr('Max. Load Unbalance'))
            castellation.setValue('allowFreeStandingZoneFaces', self._ui.allowFreeStandingZoneFaces.isChecked())

            self._db.commit(castellation)
            app.db.commit(self._db)

            self._db = app.db.checkout()

            return True
        except DBError as e:
            await AsyncMessageBox().information(self._widget, self.tr('Input Error'), e.toMessage())
            return False

    def _connectSignalsSlots(self):
        self._ui.surfaceRefinementAdd.clicked.connect(lambda: self._openSurfaceRefinementDialog())
        self._ui.volumeRefinementAdd.clicked.connect(lambda: self._openVolumeRefinementDialog())
        self._ui.refine.clicked.connect(self._refine)
        self._ui.castellationReset.clicked.connect(self._reset)

    def _load(self):
        self._db = app.db.checkout()

        castellation = self._db.getElement('castellation')
        self._ui.nCellsBetweenLevels.setText(castellation.value('nCellsBetweenLevels'))
        self._ui.resolveFeatureAngle.setText(castellation.value('resolveFeatureAngle'))
        self._ui.keepNonManifoldEdges.setChecked(castellation.value('vtkNonManifoldEdges'))
        self._ui.keepOpenEdges.setChecked(castellation.value('vtkBoundaryEdges'))

        self._ui.maxGlobalCells.setText(castellation.value('maxGlobalCells'))
        self._ui.maxLocalCells.setText(castellation.value('maxLocalCells'))
        self._ui.minRefinementCells.setText(castellation.value('minRefinementCells'))
        self._ui.maxLoadUnbalance.setText(castellation.value('maxLoadUnbalance'))
        self._ui.allowFreeStandingZoneFaces.setChecked(castellation.value('allowFreeStandingZoneFaces'))

        self._ui.surfaceRefinement.clear()
        self._ui.volumeRefinement.clear()

        groups = {GeometryType.SURFACE.value: set(), GeometryType.VOLUME.value: set()}
        for gId, geometry in self._db.getElements('geometry').items():
            if group := geometry.value('castellationGroup'):
                groups[geometry.value('gType')].add(group)

        for groupId, element in castellation.elements('refinementSurfaces').items():
            if groupId in groups[GeometryType.SURFACE.value]:
                surfaceRefinement = element.element('surfaceRefinement')
                self._addSurfaceRefinementItem(
                    groupId, element.value('groupName'),
                    surfaceRefinement.value('minimumLevel'), surfaceRefinement.value('maximumLevel'))
            else:
                self._db.removeElement('castellation/refinementSurfaces', groupId)

        for groupId, element in castellation.elements('refinementVolumes').items():
            if groupId in groups[GeometryType.VOLUME.value]:
                self._addVolumeRefinementItem(groupId,
                                              element.value('groupName'), element.value('volumeRefinementLevel'))
            else:
                self._db.removeElement('castellation/refinementVolumes', groupId)

        self._loaded = True
        self._updateControlButtons()

    def _openSurfaceRefinementDialog(self, groupId=None):
        self._dialog = SurfaceRefinementDialog(self._widget, self._db, groupId)
        if self._locked:
            self._dialog.disableEdit()
        else:
            self._dialog.accepted.connect(self._surfaceRefinementDialogAccepted)
        self._dialog.open()

    def _openVolumeRefinementDialog(self, groupId=None):
        self._dialog = VolumeRefinementDialog(self._widget, self._db, groupId)
        if self._locked:
            self._dialog.disableEdit()
        else:
            self._dialog.accepted.connect(self._volumeRefinementDialogAccepted)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _refine(self):
        if self._cm:
            self._cm.cancel()
            return

        nCellsBetweenLevels = int(self._ui.nCellsBetweenLevels.text())
        if nCellsBetweenLevels < 1:
            await AsyncMessageBox().warning(self._widget, self.tr('Invalid Parameter'), self.tr('"Number of Cells between Levels" should be bigger than or equal to 1'))
            return


        buttonText = self._ui.refine.text()
        try:
            if not await self.save():
                return

            self._disableEdit()
            self._disableControlsForRunning()
            self._ui.refine.setText(self.tr('Cancel'))

            progressDialog = ProgressDialog(self._widget, self.tr('Castellation Refinement'))
            progressDialog.setLabelText(self.tr('Updating Configurations'))
            progressDialog.open()

            progressDialog.setLabelText(self.tr('Writing Geometry Files'))
            self._writeGeometryFiles(progressDialog)

            snapDict = SnappyHexMeshDict(castellationMesh=True).build()
            if app.db.elementCount('region') > 1:
                snapDict.write()
            else:
                snapDict.updateForCellZoneInterfacesSnap().write()

            progressDialog.close()

            console = app.consoleView
            console.clear()

            self._cm = RunParallelUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
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

            await AsyncMessageBox().information(self._widget, self.tr('Complete'), self.tr('Castellation refinement is completed.'))
        except ProcessError as e:
            self.clearResult()
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Castellation refinement Failed. [') + str(e.returncode) + ']')
        except CanceledException:
            self.clearResult()
            await AsyncMessageBox().information(self._widget, self.tr('Canceled'),
                                                self.tr('Castellation refinement has been canceled.'))
        finally:
            self._enableEdit()
            self._enableControlsForSettings()
            self._ui.refine.setText(buttonText)
            self._cm = None

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()

    def _surfaceRefinementDialogAccepted(self):
        element = self._dialog.dbElement()
        if self._dialog.isCreationMode():
            self._addSurfaceRefinementItem(self._dialog.groupId(), element.getValue('groupName'),
                                           element.getValue('surfaceRefinement/minimumLevel'),
                                           element.getValue('surfaceRefinement/maximumLevel'))
        else:
            self._ui.surfaceRefinement.item(self._dialog.groupId()).update([
                element.getValue('groupName'),
                element.getValue('surfaceRefinement/minimumLevel'), element.getValue('surfaceRefinement/maximumLevel')])

    def _addSurfaceRefinementItem(self, groupId, name, minLevel, maxLevel):
        item = ListItemWithButtons(groupId, [name, minLevel, maxLevel])
        item.editClicked.connect(lambda: self._openSurfaceRefinementDialog(groupId))
        item.removeClicked.connect(lambda: self._removeSurfaceRefinement(groupId))
        self._ui.surfaceRefinement.addItem(item)

    def _removeSurfaceRefinement(self, groupId):
        self._db.removeElement('castellation/refinementSurfaces', groupId)
        self._db.updateElements('geometry', 'castellationGroup', None,
                                       lambda i, e: e['castellationGroup'] == groupId)

        self._ui.surfaceRefinement.removeItem(groupId)

    def _volumeRefinementDialogAccepted(self):
        element = self._dialog.dbElement()
        if self._dialog.isCreationMode():
            self._addVolumeRefinementItem(self._dialog.groupId(), element.getValue('groupName'),
                                          element.getValue('volumeRefinementLevel'))
        else:
            self._ui.volumeRefinement.item(self._dialog.groupId()).update(
                [element.getValue('groupName'), element.getValue('volumeRefinementLevel')])

    def _addVolumeRefinementItem(self, groupId, name, level):
        item = ListItemWithButtons(groupId, [name, level])
        item.editClicked.connect(lambda: self._openVolumeRefinementDialog(groupId))
        item.removeClicked.connect(lambda: self._removeVolumeRefinement(groupId))
        self._ui.volumeRefinement.addItem(item)

    def _removeVolumeRefinement(self, groupId):
        self._db.removeElement('castellation/refinementVolumes', groupId)
        self._db.updateElements('geometry', 'castellationGroup', None,
                                       lambda i, e: e['castellationGroup'] == groupId)

        self._ui.volumeRefinement.removeItem(groupId)

    def _writeGeometryFiles(self, progressDialog):
        def writeGeometryFile(path: Path, pd):
            writer = vtkSTLWriter()
            writer.SetFileName(str(path))
            writer.SetInputData(pd)
            writer.Write()

        filePath = app.fileSystem.triSurfacePath()
        geometryManager = app.window.geometryManager
        geometries = app.db.getElements('geometry')

        for gId, geometry in geometries.items():
            if progressDialog.isCanceled():
                return

            if geometryManager.isBoundingHex6(gId):
                continue

            if geometry.value('gType') == GeometryType.SURFACE.value:
                polyData = geometryManager.polyData(gId)
                _writeFeatureFile(filePath / f"{geometry.value('name')}.obj", polyData)

                if geometry.value('shape') == Shape.TRI_SURFACE_MESH.value:
                    volume = geometries[geometry.value('volume')] if geometry.value('volume') else None
                    if (geometry.value('cfdType') != CFDType.NONE.value
                            or geometry.value('castellationGroup')
                            or (volume is not None and volume.value('cfdType') != CFDType.NONE.value)):
                        writeGeometryFile(filePath / f"{geometry.value('name')}.stl", polyData)

            else:  # geometry['gType'] == GeometryType.VOLUME.value
                if geometry.value('shape') == Shape.TRI_SURFACE_MESH.value and (
                        geometry.value('cfdType') != CFDType.NONE.value or geometry.value('castellationGroup')):
                    appendFilter = vtkAppendPolyData()
                    for surfaceId in geometryManager.subSurfaces(gId):
                        appendFilter.AddInputData(geometryManager.polyData(surfaceId))

                    cleanFilter = vtkCleanPolyData()
                    cleanFilter.SetInputConnection(appendFilter.GetOutputPort())
                    cleanFilter.Update()

                    writeGeometryFile(filePath / f"{geometry.value('name')}.stl", cleanFilter.GetOutput())

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.refine.hide()
            self._ui.castellationReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.refine.show()
            self._ui.castellationReset.hide()
            self._setNextStepEnabled(False)

    def _enableStep(self):
        self._enableEdit()
        self._ui.castellationButtons.setEnabled(True)

    def _disableStep(self):
        self._disableEdit()
        self._ui.castellationButtons.setEnabled(False)

    def _enableEdit(self):
        self._ui.castellationConfiguration.setEnabled(True)
        self._ui.castellationAdvanced.setEnabled(True)
        self._ui.surfaceRefinementAdd.setEnabled(True)
        self._ui.surfaceRefinement.enableEdit()
        self._ui.volumeRefinementAdd.setEnabled(True)
        self._ui.volumeRefinement.enableEdit()

    def _disableEdit(self):
        self._ui.castellationConfiguration.setEnabled(False)
        self._ui.castellationAdvanced.setEnabled(False)
        self._ui.surfaceRefinementAdd.setEnabled(False)
        self._ui.surfaceRefinement.disableEdit()
        self._ui.volumeRefinementAdd.setEnabled(False)
        self._ui.volumeRefinement.disableEdit()
