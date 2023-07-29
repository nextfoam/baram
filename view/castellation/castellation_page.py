#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

import qasync
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkCleanPolyData, vtkFeatureEdges
from vtkmodules.vtkIOGeometry import vtkSTLWriter, vtkOBJWriter

from app import app
from db.configurations_schema import GeometryType, Shape, CFDType
from db.simple_db import elementToVector
from openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from rendering.vtk_loader import hexPolyData
from libbaram.run import runUtility
from view.geometry.geometry_manager import platePolyData
from view.step_page import StepPage
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from .region_tab import RegionTab
from .castellation_tab import CastellationTab
from .castellation_advanced_dialog import CastellationAdvancedDialog, DEFAULT_FEATURE_LEVEL
from .castellation_page_ui import Ui_CastellationPage


class Tab(Enum):
    REGION = 0
    CASTELLATION = auto()


class CastellationPage(StepPage):
    OUTPUT_TIME = 1

    def __init__(self):
        super().__init__()
        self._ui = Ui_CastellationPage()
        self._ui.setupUi(self)

        self._ui.tabWidget.setCurrentIndex(0)

        self._regionTab = RegionTab(self, self._ui)
        self._castellationTab = CastellationTab(self, self._ui)

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

        self._castellationTab.load(self._refinementSurfaces, self._refinementVolumes)

        self._advancedDialog = None

        self._connectSignalsSlots()

        self._ui.reset.hide()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._currentTabChanged(self._ui.tabWidget.currentIndex())

        return super().showEvent(ev)

    def hideEvent(self, ev):
        if not ev.spontaneous():
            self._regionTab.deactivated()

        return super().hideEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.tabWidget.currentChanged.connect(self._currentTabChanged)
        self._ui.advanced.clicked.connect(self._advancedConfigure)
        self._ui.refine.clicked.connect(self._refine)

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

    def _advancedConfigure(self):
        self._advancedDialog = CastellationAdvancedDialog(self, self._refinementFeatures)
        self._advancedDialog.open()

    @qasync.asyncSlot()
    async def _refine(self):
        progressDialog = ProgressDialogSimple(self, self.tr('Castellation Refinement'), True)
        progressDialog.setLabelText(self.tr('Updating Configurations'))
        progressDialog.open()

        self._castellationTab.save()
        if self._advancedDialog is None or not self._advancedDialog.isAccepted():
            self._updateFeatureLevels()

        progressDialog.setLabelText(self.tr('Writing Geometry Files'))
        self._writeGeometryFiles(progressDialog)
        SnappyHexMeshDict(castellationMesh=True).build().write()

        progressDialog.setLabelText(self.tr('Refining Castellation'))
        proc = await runUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot())
        if await proc.wait():
            progressDialog.finish(self.tr('Castellation Refinement Failed.'))

        progressDialog.hideCancelButton()
        meshManager = app.window.meshManager
        meshManager.progress.connect(progressDialog.setLabelText)
        await meshManager.load()

        progressDialog.close()

    def _updateFeatureLevels(self):
        db = app.db.checkout('castellation')
        for geometry in self._refinementFeatures:
            if not db.keyExists('features', geometry['gId']):
                e = db.newElement('features')
                e.setValue('level', DEFAULT_FEATURE_LEVEL)
                db.addElement('features', e, geometry['gId'])

        app.db.commit(db)

    def _writeGeometryFiles(self, progressDialog):
        def writeGeometryFile(name, pd):
            writer = vtkSTLWriter()
            writer.SetFileName(str(filePath / f'{name}.stl'))
            writer.SetInputData(pd)
            writer.Write()

        def writeFeatureFile(name, pd):
            edges = vtkFeatureEdges()
            edges.SetInputData(pd)
            edges.SetNonManifoldEdges(app.db.getBool('castellation/vtkNonManifoldEdges'))
            edges.SetBoundaryEdges(app.db.getBool('castellation/vtkBoundaryEdges'))
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
