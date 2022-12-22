#!/usr/bin/env python
# -*- coding: utf-8 -*-
import vtk
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
        # self._actor.GetProperty().SetColor(0.8, 0.8, 0.8)
        # self._actor.GetProperty().SetOpacity(1.0)
        # self._actor.GetProperty().SetEdgeVisibility(True)
        # self._actor.GetProperty().SetEdgeColor(0.1, 0.0, 0.3)
        # self._actor.GetProperty().SetLineWidth(1.0)

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
    currentActorChanged = Signal()

    def __init__(self):
        super().__init__()

        self._active = False
        self._view = app.meshDock
        self._actorInfos = {}
        self._currentId = None

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

    def actorInfos(self):
        return self._actorInfos.values()

    def setActorInfo(self, id_, actorInfo):
        self._actorInfos[id_] = actorInfo

    def actorInfo(self, id_):
        if id_ in self._actorInfos:
            return self._actorInfos[id_]

    def currentId(self):
        return self._currentId

    def currentActor(self):
        if self._currentId:
            return self._actorInfos[self._currentId].actor

        return None

    def showActor(self, id_):
        self._view.addActor(self._actorInfos[id_])
        self._view.update()

    def hideActor(self, id_):
        self._view.removeActor(self._actorInfos[id_])
        self._view.update()

    def actorPicked(self, actor):
        self.setCurrentId(self._findActorInfo(actor))
        self.currentActorChanged.emit()

    def setCurrentId(self, id_):
        self._highlightActor(id_)
        self._currentId = id_

    def _findActorInfo(self, actor):
        for id_ in self._actorInfos:
            if self._actorInfos[id_].actor == actor:
                return id_

        return None

    def _highlightActor(self, id_):
        return


class MeshActors(VtkViewModel):
    def __init__(self):
        super().__init__()

    def isMesh(self):
        return True

    def _highlightActor(self, id_):
        # If we picked something before, reset the property of the other actors
        if currentActor := self.currentActor():
            self._view.applyDisplayMode(currentActor)

        actor = None
        if id_:
            # Highlight the picked actor by changing its properties
            actor = self._actorInfos[id_].actor
            actor.GetProperty().SetColor(1, 1, 1)
            actor.GetProperty().SetEdgeColor(1, 1, 1)
            actor.GetProperty().EdgeVisibilityOn()
            actor.GetProperty().SetRepresentationToSurface()

        if actor != currentActor:
            self._view.update()
