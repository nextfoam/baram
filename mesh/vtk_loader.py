#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vtk
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper
from vtkmodules.vtkIOLegacy import vtkPolyDataReader

from app import app


def loadVtkFile(file):
    if not file.exists():
        return None

    r = vtkPolyDataReader()
    r.SetFileName(file)
    r.Update()

    actorInfo = ActorInfo(r.GetOutput())
    actorInfo.visibility = False

    return actorInfo


class ActorInfo:
    # It is not clear if the references of these two values should be kept
    #    dataset: vtk.vtkDataObject
    #    gFilter: vtk.vtkGeometryFilter

    def __init__(self, inputData):
        self._visibility = True
        self._selected = False

        self._mapper = vtkPolyDataMapper()
        self._actor = vtk.vtkQuadricLODActor()    # vtkActor()

        self._mapper.SetInputData(inputData)
        self._actor.SetMapper(self._mapper)
        self._actor.GetProperty().SetColor(0.8, 0.8, 0.8)
        self._actor.GetProperty().SetOpacity(1.0)
        self._actor.GetProperty().SetEdgeVisibility(True)
        self._actor.GetProperty().SetEdgeColor(0.1, 0.0, 0.3)
        self._actor.GetProperty().SetLineWidth(1.0)

    @property
    def actor(self):
        return self._actor

    @property
    def visibility(self):
        return self._visibility

    @visibility.setter
    def visibility(self, visibility):
        self._visibility = visibility


class VtkViewModel:
    def __init__(self):
        self._active = False
        self._view = app.meshDock

    def isMesh(self):
        return False

    def activate(self):
        self._active = True
        self._view.setModel(self)

    def deactivate(self):
        self._active = False
        self._view.clear()

    def isActive(self):
        return self._active


class VtkMesh(VtkViewModel):
    def __init__(self, vtkMesh):
        super().__init__()
        self._vtkMesh = vtkMesh
        self._actorInfos = []

        for rname in vtkMesh:
            if 'boundary' in vtkMesh[rname]:
                for bcname, actorInfo in vtkMesh[rname]['boundary'].items():
                    self._addActorInfo(actorInfo)

    def showActor(self, rname, boundary):
        self._view.addActor(self._vtkMesh[rname]['boundary'][boundary])
        self._view.update()

    def hideActor(self, rname, boundary):
        self._view.removeActor(self._vtkMesh[rname]['boundary'][boundary])
        self._view.update()

    def isMesh(self):
        return True

    def actorInfos(self):
        return self._actorInfos

    def _addActorInfo(self, actorInfo):
        self._actorInfos.append(actorInfo)
