#!/usr/bin/env python
# -*- coding: utf-8 -*-
import vtk
# import vtkmodules
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper
from vtkmodules.vtkIOLegacy import vtkPolyDataReader
from PySide6.QtCore import QObject, Signal

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


class VtkViewModel(QObject):
    actorPicked = Signal()

    def __init__(self):
        super().__init__()

        self._active = False
        self._view = app.meshDock
        self._actorInfos = {}
        self._isMesh = False
        self._pickedId = None

    def setToMesh(self):
        self._isMesh = True

    def isMesh(self):
        return self._isMesh

    def activate(self):
        self._active = True
        self._view.setModel(self)

    def deactivate(self):
        self._active = False
        self._view.clear()

    def isActive(self):
        return self._active

    def actorInfos(self):
        return self._actorInfos.values()

    def addActorInfo(self, id_, actorInfo):
        self._actorInfos[id_] = actorInfo

    def pickedId(self):
        return self._pickedId

    def showActor(self, id_):
        self._view.addActor(self._actorInfos[id_])
        self._view.update()

    def hideActor(self, id_):
        self._view.removeActor(self._actorInfos[id_])
        self._view.update()

    def setPickedActor(self, actor):
        self._pickedId = self._findActorInfo(actor)
        self.actorPicked.emit()

    def pickActor(self, id_):
        self._pickedId = id_
        self._view.pickActor(self._actorInfos[id_].actor if id_ else None)

    def _findActorInfo(self, actor):
        for id_ in self._actorInfos:
            if self._actorInfos[id_].actor == actor:
                return id_

        return None
