#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import re
from io import StringIO

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import VTK_POLY_DATA
from vtkmodules.vtkFiltersCore import vtkFeatureEdges
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from vtkmodules.vtkRenderingLOD import vtkQuadricLODActor

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.system.fv_schemes import FvSchemes
from baramFlow.openfoam.system.fv_solution import FvSolution
from baramFlow.view.dock_widgets.rendering_dock import DisplayMode
from libbaram.exception import CanceledException
from libbaram.run import RunParallelUtility


def getActor(dataset):
    gFilter = vtkGeometryFilter()
    gFilter.SetInputData(dataset)
    gFilter.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(gFilter.GetOutput())
    mapper.ScalarVisibilityOff()

    actor = vtkQuadricLODActor()    # vtkActor()
    actor.SetMapper(mapper)

    return actor


def getFeatureActor(dataset):
    edges = vtkFeatureEdges()
    edges.SetInputData(dataset)
    edges.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(edges.GetOutput())
    mapper.ScalarVisibilityOff()

    actor = vtkActor()
    actor.SetMapper(mapper)

    return actor


_applyDisplayMode = {
    DisplayMode.DISPLAY_MODE_POINTS         : lambda actor: _applyPointsMode(actor),
    DisplayMode.DISPLAY_MODE_WIREFRAME      : lambda actor: _applyWireframeMode(actor),
    DisplayMode.DISPLAY_MODE_SURFACE        : lambda actor: _applySurfaceMode(actor),
    DisplayMode.DISPLAY_MODE_SURFACE_EDGE   : lambda actor: _applySurfaceEdgeMode(actor),
    DisplayMode.DISPLAY_MODE_FEATURE        : lambda actor: _applyFeatureMode(actor)
}


def _applyPointsMode(actor):
    actor.GetProperty().SetPointSize(3)
    actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('Gainsboro'))
    actor.GetProperty().SetRepresentationToPoints()


def _applyWireframeMode(actor):
    actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('Gainsboro'))
    actor.GetProperty().SetLineWidth(1.0)
    actor.GetProperty().SetRepresentationToWireframe()


def _applySurfaceMode(actor):
    actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('Gainsboro'))
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().EdgeVisibilityOff()


def _applySurfaceEdgeMode(actor):
    actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('Gainsboro'))
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
    actor.GetProperty().SetLineWidth(1.0)


def _applyFeatureMode(actor):
    actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('Gainsboro'))
    actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('WhiteSmoke'))
    actor.GetProperty().SetLineWidth(1.0)


def _applyHighlight(actor):
    actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('White'))
    actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Magenta'))
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().SetLineWidth(2)


class ActorInfo:
    def __init__(self, dataSet):
        self._visibility = True
        self._selected = False
        self._dataSet = dataSet
        self._face = None
        self._feature = None

        self._face = getActor(dataSet)
        if dataSet.GetDataObjectType() == VTK_POLY_DATA:
            self._feature = getFeatureActor(dataSet)

    @property
    def face(self):
        return self._face

    @property
    def feature(self):
        return self._feature

    @property
    def dataSet(self):
        return self._dataSet

    def actor(self, featureMode):
        return self._feature if featureMode else self._face

    @property
    def visibility(self):
        return self._visibility

    @visibility.setter
    def visibility(self, visibility):
        self._visibility = visibility


class RenderingModel(QObject):
    def __init__(self):
        super().__init__()

        self._view = app.renderingView
        self._view.viewClosed.connect(self._viewClosed)

    def _viewClosed(self):
        self._view = None


class MeshModel(RenderingModel):
    currentActorChanged = Signal()

    def __init__(self):
        super().__init__()

        self._actorInfos = {}
        self._currentId = None
        self._featureMode = False
        self._hasFeatures = True
        self._bounds = None
        self._activation = False

        self._numCells = None
        self._smallestCellVolume = None
        self._largestCellVolume = None

        self._connectSignalsSlots()

    def activate(self):
        if not self._activation and self._view:
            renderingMode = self._view.renderingMode()
            self._featureMode = renderingMode == DisplayMode.DISPLAY_MODE_FEATURE and self._hasFeatures
            for actorInfo in self._actorInfos.values():
                if actorInfo.visibility:
                    actor = actorInfo.actor(self._featureMode)
                    _applyDisplayMode[renderingMode](actor)
                    self._view.addActor(actor)

            self._view.fitCamera()
            self._activation = True

    def deactivate(self):
        if self._view is None:
            return

        for actorInfo in self._actorInfos.values():
            if actorInfo.visibility:
                self._view.removeActor(actorInfo.actor(self._featureMode))

        self._view.refresh()
        self._activation = False

    def setActorInfo(self, id_, actorInfo):
        self._actorInfos[id_] = actorInfo

    def actorInfo(self, id_):
        if id_ in self._actorInfos:
            return self._actorInfos[id_]

    def currentId(self):
        return self._currentId

    def currentActor(self):
        if self._currentId:
            actorInfo = self._actorInfos[self._currentId]
            return actorInfo.feature if self._featureMode else actorInfo.face

        return None

    def showActor(self, id_):
        if not self._actorInfos[id_].visibility:
            actor = self._actorInfos[id_].actor(self._featureMode)
            self._view.addActor(actor)
            self._applyDisplayMode(actor)
            self._actorInfos[id_].visibility = True
            self._view.refresh()

    def hideActor(self, id_):
        if self._actorInfos[id_].visibility:
            self._view.removeActor(self._actorInfos[id_].actor(self._featureMode))
            self._actorInfos[id_].visibility = False
            self._view.refresh()

    def setCurrentId(self, id_):
        self._highlightActor(id_)
        self._currentId = id_

    def showCulling(self):
        for a in self._actorInfos.values():
            a.actor(self._featureMode).GetProperty().FrontfaceCullingOn()

    def hideCulling(self):
        for a in self._actorInfos.values():
            a.actor(self._featureMode).GetProperty().FrontfaceCullingOff()

    async def getBounds(self):
        if not self._bounds:
            self._bounds = [
                min([a.face.GetBounds()[0] for a in self._actorInfos.values()]),
                max([a.face.GetBounds()[1] for a in self._actorInfos.values()]),
                min([a.face.GetBounds()[2] for a in self._actorInfos.values()]),
                max([a.face.GetBounds()[3] for a in self._actorInfos.values()]),
                min([a.face.GetBounds()[4] for a in self._actorInfos.values()]),
                max([a.face.GetBounds()[5] for a in self._actorInfos.values()])
            ]

        return self._bounds

    async def getNumberOfCells(self):
        if self._numCells is None:
            await self._checkMesh()

        return self._numCells

    async def getSmallestCellVolume(self):
        if self._smallestCellVolume is None:
            await self._checkMesh()

        return self._smallestCellVolume

    async def getLargestCellVolume(self):
        if self._largestCellVolume is None:
            await self._checkMesh()

        return self._largestCellVolume

    def _connectSignalsSlots(self):
        self._view.renderingModeChanged.connect(self._changeRenderingMode)
        self._view.actorPicked.connect(self._actorPicked)

    def _changeRenderingMode(self, displayMode):
        if displayMode == DisplayMode.DISPLAY_MODE_FEATURE and self._hasFeatures:
            self._featureMode = True
            for a in self._actorInfos.values():
                if a.visibility:
                    self._view.removeActor(a.face)
                    self._view.addActor(a.feature)
                self._applyDisplayMode(a.feature)
        else:
            featureModeChanged = self._featureMode
            self._featureMode = False
            for a in self._actorInfos.values():
                if a.visibility:
                    if featureModeChanged:
                        self._view.removeActor(a.feature)
                        self._view.addActor(a.face)
                    self._applyDisplayMode(a.face)

        self._view.refresh()

    def _findActorInfo(self, actor):
        for id_ in self._actorInfos:
            if self._actorInfos[id_].actor(self._featureMode) == actor:
                return id_

        return None

    def _highlightActor(self, id_):
        # Reset properties of unselected actors
        if currentActor := self.currentActor():
            _applyDisplayMode[self._view.renderingMode()](currentActor)

        actor = None
        if id_:
            _applyHighlight(self._actorInfos[id_].actor(self._featureMode))

        if actor != currentActor:
            self._view.refresh()

    def _applyDisplayMode(self, actor):
        if actor == self.currentActor():
            _applyHighlight(actor)
        else:
            _applyDisplayMode[self._view.renderingMode()](actor)

    def _actorPicked(self, actor):
        self.setCurrentId(self._findActorInfo(actor))
        self.currentActorChanged.emit()

    async def _checkMesh(self):
        def _stdout(output):
            ioStream.write(output+'\n')

        ioStream = StringIO()
        cm = None

        # "checkMesh" requires fvSchemes and fvSolution
        # They are not available right after importing Multi-Region mesh files
        regions = coredb.CoreDB().getRegions()
        for rname in regions:
            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()

        try:
            caseRoot = FileSystem.caseRoot()
            cm = RunParallelUtility('checkMesh', '-allRegions', '-time', '0', '-case', caseRoot,
                                    cwd=caseRoot, parallel=parallel.getEnvironment())
            cm.output.connect(_stdout)
            await cm.start()
            await cm.wait()

            numCells = 0
            smallestVolume = 1000000000  # 1km^3, sufficiently large value for smallestVolume
            largestVolume = 0  # sufficiently small value for largestVolume

            numCellPattern = r'^\s+cells:\s+(?P<numCells>[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)'
            volumePattern = r'Min volume = (?P<minVol>[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\. Max volume = (?P<maxVol>[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\.'

            ioStream.seek(0)
            for line in ioStream.readlines():
                m = re.search(numCellPattern, line)
                if m is not None:
                    numCells += int(m.group('numCells'))
                    continue

                m = re.search(volumePattern, line)
                if m is not None:
                    minVol = float(m.group('minVol'))
                    maxVol = float(m.group('maxVol'))
                    if minVol < smallestVolume:
                        smallestVolume = minVol
                    if maxVol > largestVolume:
                        largestVolume = maxVol

            ioStream.close()

            self._numCells = numCells
            self._largestCellVolume = largestVolume
            self._smallestCellVolume = smallestVolume

        except CanceledException:
            pass

        except asyncio.CancelledError:
            if cm:
                cm.cancel()
            else:
                raise CanceledException


