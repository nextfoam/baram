#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from enum import Enum, auto

import qasync
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkCleanPolyData, vtkFeatureEdges
from vtkmodules.vtkIOGeometry import vtkSTLWriter, vtkOBJWriter
from PySide6.QtWidgets import QMessageBox

from app import app
from db.configurations_schema import GeometryType, Shape, CFDType
from db.simple_db import elementToVector
from openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from rendering.vtk_loader import hexPolyData
from libbaram.run import runUtility
from libbaram.process import Processor, ProcessError
from view.geometry.geometry_manager import platePolyData
from view.step_page import StepPage
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from .region_tab import RegionTab
from .castellation_tab import CastellationTab
from .castellation_advanced_dialog import CastellationAdvancedDialog, DEFAULT_FEATURE_LEVEL


class Tab(Enum):
    REGION = 0
    CASTELLATION = auto()


class CastellationPage(StepPage):
    OUTPUT_TIME = 1

    def __init__(self, ui):
        super().__init__(ui, ui.castellationPage)

        self._ui.tabWidget.setCurrentIndex(0)

        self._regionTab = RegionTab(self._ui)
        self._castellationTab = CastellationTab(self._ui)

        self._refinementSurfaces = None
        self._refinementVolumes = None
        self._refinementFeatures = None

        self._advancedDialog = None
        self._loaded = False

        self._connectSignalsSlots()

    def lock(self):
        self._regionTab.lock()
        self._castellationTab.lock()

    def unlock(self):
        self._regionTab.unlock()
        self._castellationTab.unlock()

    def open(self):
        self._load()

    def selected(self):
        if not self._loaded:
            self._load()

        self._updateControlButtons()
        self._currentTabChanged(self._ui.tabWidget.currentIndex())

    def deselected(self):
        self._regionTab.deactivated()

    def save(self):
        self._castellationTab.save()

        if self._advancedDialog is None or not self._advancedDialog.isAccepted():
            db = app.db.checkout('castellation')
            db.removeAllElements('features')

            for geometry in self._refinementFeatures:
                e = db.newElement('features')
                e.setValue('level', DEFAULT_FEATURE_LEVEL)
                db.addElement('features', e, geometry['gId'])

            app.db.commit(db)

        return self._castellationTab.save()

    def _connectSignalsSlots(self):
        self._ui.tabWidget.currentChanged.connect(self._currentTabChanged)
        self._ui.castellationAdvanced.clicked.connect(self._advancedConfigure)
        self._ui.refine.clicked.connect(self._refine)
        self._ui.castellationReset.clicked.connect(self._reset)

    def _currentTabChanged(self, index):
        if index == Tab.REGION.value:
            app.window.geometryManager.showActors()
            app.window.meshManager.hideActors()
            self._regionTab.activated()
        else:
            self._regionTab.deactivated()
            if app.fileSystem.timePath(self.OUTPUT_TIME).exists():
                app.window.geometryManager.showActors()
                app.window.meshManager.showActors()
            else:
                app.window.geometryManager.showActors()
                app.window.meshManager.hideActors()

    def _load(self):
        self._advancedDialog = None

        self._refinementSurfaces = []
        self._refinementVolumes = []
        self._refinementFeatures = []

        for gId, geometry in app.window.geometryManager.geometries().items():
            if geometry['cfdType'] != CFDType.NONE.value:
                if geometry['gType'] == GeometryType.SURFACE.value:
                    self._refinementSurfaces.append(geometry)
                    if geometry['shape'] not in (Shape.CYLINDER.value, Shape.SPHERE.value):
                        self._refinementFeatures.append(geometry)
                else:
                    self._refinementVolumes.append(geometry)

        self._regionTab.load()
        self._castellationTab.load(self._refinementSurfaces, self._refinementVolumes)

        self._loaded = True
        self._updateControlButtons()

    def _advancedConfigure(self):
        self._advancedDialog = CastellationAdvancedDialog(self._widget, self._refinementFeatures)
        self._advancedDialog.open()

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

            progressDialog = ProgressDialogSimple(self._widget, self.tr('Loading Mesh'), False)
            progressDialog.setLabelText(self.tr('Loading Mesh'))
            progressDialog.open()

            meshManager = app.window.meshManager
            meshManager.clear()
            meshManager.progress.connect(progressDialog.setLabelText)
            await meshManager.load()

            self._updateControlButtons()
            progressDialog.close()
        except ProcessError as e:
            self.clearResult()
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Castellation Refinement Failed. [') + e.returncode + ']')
        finally:
            self.unlock()

    def _reset(self):
        self.clearResult()
        self._updateControlButtons()

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

        for geometry in self._refinementSurfaces:
            if progressDialog.isCanceled():
                return

            shape = geometry['shape']
            if shape == Shape.TRI_SURFACE_MESH.value:
                polyData = app.db.geometryPolyData(geometry['path'])
                writeGeometryFile(geometry['name'], polyData)
                writeFeatureFile(geometry['name'], polyData)
            elif geometry['cfdType'] not in (CFDType.NONE.value, GeometryType.SURFACE.value):
                volume = app.window.geometryManager.geometry(geometry['volume'])

                if shape == Shape.HEX.value:
                    polyData = hexPolyData(elementToVector(volume['point1']), elementToVector(volume['point2']))
                    writeFeatureFile(geometry['name'], polyData)
                elif shape in Shape.PLATES.value:
                    polyData = platePolyData(shape, volume)
                    writeFeatureFile(geometry['name'], polyData)

        for geometry in self._refinementVolumes:
            if progressDialog.isCanceled():
                return

            if geometry['shape'] == Shape.TRI_SURFACE_MESH.value:
                appendFilter = vtkAppendPolyData()
                for surfaceId in app.window.geometryManager.subSurfaces(geometry['gId']):
                    appendFilter.AddInputData(
                        app.db.geometryPolyData(app.window.geometryManager.geometry(surfaceId)['path']))

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
