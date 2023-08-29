#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

import qasync
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkCleanPolyData, vtkFeatureEdges
from vtkmodules.vtkIOGeometry import vtkSTLWriter, vtkOBJWriter
from PySide6.QtWidgets import QMessageBox

from app import app
from db.configurations_schema import GeometryType, Shape, CFDType
from db.simple_schema import DBError
from openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from libbaram.run import runUtility
from libbaram.process import Processor, ProcessError
from view.step_page import StepPage
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from view.widgets.list_table import ListItemWithButtons
from view.widgets.multi_selector_dialog import SelectorItem
from .surface_refinement_dialog import SurfaceRefinementDialog
from .volume_refinement_dialog import VolumeRefinementDialog


from view.main_window.main_window_ui import Ui_MainWindow


class CastellationPage(StepPage):
    OUTPUT_TIME = 1

    def __init__(self, ui:Ui_MainWindow):
        super().__init__(ui, ui.castellationPage)

        self._loaded = False
        self._db = None
        self._dialog = None

        self._surfaces = None
        self._volumes = None
        self._selectorItems = None

        ui.castellationConfigurationHeader.setContents(ui.castellationConfiguration)
        ui.castellationAdvancedHeader.setContents(ui.castellationAdvanced)
        ui.surfaceRefinementHeader.setContents(ui.surfaceRefinement)
        ui.volumeRefinementHeader.setContents(ui.volumeRefinement)

        ui.surfaceRefinement.setHeaderWithWidth([0, 0, 16, 16])
        ui.volumeRefinement.setHeaderWithWidth([0, 0, 16, 16])

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
            self._db.setValue('nCellsBetweenLevels', self._ui.nCellsBetweenLevels.text(),
                              self.tr('Number of Cells between Levels'))
            self._db.setValue('resolveFeatureAngle', self._ui.resolveFeatureAngle.text(),
                              self.tr('Feature Angle Threshold'))
            self._db.setValue('vtkNonManifoldEdges', self._ui.keepNonManifoldEdges.isChecked())
            self._db.setValue('vtkBoundaryEdges', self._ui.keepOpenEdges.isChecked())

            self._db.setValue('maxGlobalCells', self._ui.maxGlobalCells.text(), self.tr('Max. Global Cell Count'))
            self._db.setValue('maxLocalCells', self._ui.maxLocalCells.text(), self.tr('Max. Local Cell Count'))
            self._db.setValue('minRefinementCells', self._ui.minRefinementCells.text(),
                              self.tr('Min.Refinement Cell Count'))
            self._db.setValue('maxLoadUnbalance', self._ui.maxLoadUnbalance.text(), self.tr('Max. Load Unbalance'))
            self._db.setValue('allowFreeStandingZoneFaces', self._ui.allowFreeStandingZoneFaces.isChecked())

            app.db.commit(self._db)
            self._db = app.db.checkout('castellation')

            return True
        except DBError as e:
            QMessageBox.information(self._widget, self.tr('Input Error'), e.toMessage())
            return False

    def _connectSignalsSlots(self):
        self._ui.surfaceRefinementAdd.clicked.connect(lambda: self._openSurfaceRefinementDialog())
        self._ui.volumeRefinementAdd.clicked.connect(lambda: self._openVolumeRefinementDialog())
        self._ui.refine.clicked.connect(self._refine)
        self._ui.castellationReset.clicked.connect(self._reset)

    def _load(self):
        self._db = app.db.checkout('castellation')

        self._ui.nCellsBetweenLevels.setText(self._db.getValue('nCellsBetweenLevels'))
        self._ui.resolveFeatureAngle.setText(self._db.getValue('resolveFeatureAngle'))
        self._ui.keepNonManifoldEdges.setChecked(self._db.getValue('vtkNonManifoldEdges'))
        self._ui.keepOpenEdges.setChecked(self._db.getValue('vtkBoundaryEdges'))

        self._ui.maxGlobalCells.setText(self._db.getValue('maxGlobalCells'))
        self._ui.maxLocalCells.setText(self._db.getValue('maxLocalCells'))
        self._ui.minRefinementCells.setText(self._db.getValue('minRefinementCells'))
        self._ui.maxLoadUnbalance.setText(self._db.getValue('maxLoadUnbalance'))
        self._ui.allowFreeStandingZoneFaces.setChecked(self._db.getValue('allowFreeStandingZoneFaces'))

        self._surfaces = {}
        self._volumes = {}
        self._selectorItems = {}

        self._ui.surfaceRefinement.clear()
        self._ui.volumeRefinement.clear()

        for gId, geometry in app.window.geometryManager.geometries().items():
            if geometry['gType'] == GeometryType.SURFACE.value:
                self._surfaces[gId] = 0
            else:
                self._volumes[gId] = 0
            self._selectorItems[gId] = SelectorItem(geometry['name'], geometry['name'], geometry['gId'])

        for groupId, element in self._db.getElements('refinementSurfaces').items():
            self._addSurfaceRefinementItem(groupId, element['groupName'], element['surfaceRefinementLevel'],
                                           element['surfaces'])

        for groupId, element in self._db.getElements('refinementVolumes').items():
            self._addVolumeRefinementItem(groupId, element['groupName'], element['volumeRefinementLevel'],
                                           element['volumes'])

        self._loaded = True
        self._updateControlButtons()

    def _openSurfaceRefinementDialog(self, groupId=None):
        dbElement = None if groupId is None else self._db.checkout(f'refinementSurfaces/{groupId}')
        surfaces = [self._selectorItems[gId] for gId, group in self._surfaces.items() if group == groupId or group == 0]

        self._dialog = SurfaceRefinementDialog(self._widget, surfaces, dbElement, groupId)
        self._dialog.accepted.connect(self._surfaceRefinementDialogAccepted)
        self._dialog.open()

    def _openVolumeRefinementDialog(self, groupId=None):
        dbElement = None if groupId is None else self._db.checkout(f'refinementVolumes/{groupId}')
        volumes = [self._selectorItems[gId] for gId, group in self._volumes.items() if group == groupId or group == 0]

        self._dialog = VolumeRefinementDialog(self._widget, volumes, dbElement, groupId)
        self._dialog.accepted.connect(self._volumeRefinementDialogAccepted)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _refine(self):
        try:
            self.lock()

            if not self.save():
                return

            progressDialog = ProgressDialogSimple(self._widget, self.tr('Castellation Refinement'))
            progressDialog.setLabelText(self.tr('Updating Configurations'))
            progressDialog.open()

            progressDialog.setLabelText(self.tr('Writing Geometry Files'))
            self._writeGeometryFiles(progressDialog)
            SnappyHexMeshDict(castellationMesh=True).build().write()

            progressDialog.close()

            console = app.consoleView
            console.clear()
            proc = await runUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(),
                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            processor = Processor(proc)
            processor.outputLogged.connect(console.append)
            processor.errorLogged.connect(console.appendError)
            await processor.run()

            await app.window.meshManager.load(self.OUTPUT_TIME)

            self._updateControlButtons()
            progressDialog.close()
        except ProcessError as e:
            self.clearResult()
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Castellation Refinement Failed. [') + str(e.returncode) + ']')
        finally:
            self.unlock()

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()

    def _surfaceRefinementDialogAccepted(self):
        element = self._dialog.dbElement()
        if self._dialog.isCreationMode():
            groupId = self._db.addElement('refinementSurfaces', element)
            self._addSurfaceRefinementItem(groupId, element.getValue('groupName'),
                                           element.getValue('surfaceRefinementLevel'), element.getValue('surfaces'))
        else:
            groupId = self._dialog.groupId()
            self._db.commit(element)
            self._unsetSurfaceGroup(groupId)
            self._setSurfaceGroup(groupId, element.getValue('surfaces'))
            self._ui.surfaceRefinement.item(groupId).update(
                [element.getValue('groupName'), element.getValue('surfaceRefinementLevel')])

    def _addSurfaceRefinementItem(self, groupId, name, level, surfaces):
        self._setSurfaceGroup(groupId, surfaces)
        item = ListItemWithButtons(groupId, [name, level])
        item.editClicked.connect(lambda: self._openSurfaceRefinementDialog(groupId))
        item.removeClicked.connect(lambda: self._removeSurfaceRefinement(groupId))
        self._ui.surfaceRefinement.addItem(item)

    def _removeSurfaceRefinement(self, groupId):
        self._db.removeElement('refinementSurfaces', groupId)
        self._unsetSurfaceGroup(groupId)
        self._ui.surfaceRefinement.removeItem(groupId)

    def _unsetSurfaceGroup(self, groupId):
        for gId in self._surfaces:
            if self._surfaces[gId] == groupId:
                self._surfaces[gId] = 0

    def _setSurfaceGroup(self, groupId, surfaces):
        for gId in surfaces:
            self._surfaces[gId] = groupId

    def _volumeRefinementDialogAccepted(self):
        element = self._dialog.dbElement()
        if self._dialog.isCreationMode():
            groupId = self._db.addElement('refinementVolumes', element)
            self._addVolumeRefinementItem(groupId, element.getValue('groupName'),
                                          element.getValue('volumeRefinementLevel'), element.getValue('volumes'))
        else:
            groupId = self._dialog.groupId()
            self._db.commit(element)
            self._unsetVolumeGroup(groupId)
            self._setVolumeGroup(groupId, element.getValue('volumes'))
            self._ui.volumeRefinement.item(groupId).update(
                [element.getValue('groupName'), element.getValue('volumeRefinementLevel')])

    def _addVolumeRefinementItem(self, groupId, name, level, volumes):
        self._setVolumeGroup(groupId, volumes)
        item = ListItemWithButtons(groupId, [name, level])
        item.editClicked.connect(lambda: self._openVolumeRefinementDialog(groupId))
        item.removeClicked.connect(lambda: self._removeVolumeRefinement(groupId))
        self._ui.volumeRefinement.addItem(item)

    def _removeVolumeRefinement(self, groupId):
        self._db.removeElement('refinementVolumes', groupId)
        self._unsetVolumeGroup(groupId)
        self._ui.volumeRefinement.removeItem(groupId)

    def _unsetVolumeGroup(self, groupId):
        for gId in self._volumes:
            if self._volumes[gId] == groupId:
                self._volumes[gId] = 0

    def _setVolumeGroup(self, groupId, volumes):
        for gId in volumes:
            self._volumes[gId] = groupId

    def _writeGeometryFiles(self, progressDialog):
        def writeGeometryFile(name, pd):
            writer = vtkSTLWriter()
            writer.SetFileName(str(filePath / f'{name}.stl'))
            writer.SetInputData(pd)
            writer.Write()

        def writeFeatureFile(name, pd):
            edges = vtkFeatureEdges()
            edges.SetInputData(pd)
            edges.SetNonManifoldEdges(app.db.getValue('castellation/vtkNonManifoldEdges'))
            edges.SetBoundaryEdges(app.db.getValue('castellation/vtkBoundaryEdges'))
            edges.Update()

            writer = vtkOBJWriter()
            writer.SetFileName(str(filePath / f"{name}.obj"))
            writer.SetInputData(edges.GetOutput())
            writer.Write()

        filePath = app.fileSystem.triSurfacePath()
        geometryManager = app.window.geometryManager

        for gId in self._surfaces:
            if progressDialog.isCanceled():
                return

            geometry = geometryManager.geometry(gId)
            if geometry['cfdType'] != CFDType.NONE.value or self._surfaces[gId]:
                polyData = geometryManager.polyData(gId)
                if geometry['shape'] == Shape.TRI_SURFACE_MESH.value:
                    writeGeometryFile(geometry['name'], polyData)
                    writeFeatureFile(geometry['name'], polyData)
                else:
                    writeFeatureFile(geometry['name'], polyData)

        for gId in self._volumes:
            if progressDialog.isCanceled():
                return

            geometry = geometryManager.geometry(gId)
            if geometry['shape'] == Shape.TRI_SURFACE_MESH.value and self._volumes[gId]:
                appendFilter = vtkAppendPolyData()
                for surfaceId in geometryManager.subSurfaces(geometry['gId']):
                    appendFilter.AddInputData(geometryManager.polyData(surfaceId))

                cleanFilter = vtkCleanPolyData()
                cleanFilter.SetInputConnection(appendFilter.GetOutputPort())
                cleanFilter.Update()

                writeGeometryFile(geometry['name'], cleanFilter.GetOutput())

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.refine.hide()
            self._ui.castellationReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.refine.show()
            self._ui.castellationReset.hide()
            self._setNextStepEnabled(False)
