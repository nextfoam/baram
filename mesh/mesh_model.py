#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal

from app import app
from view.main_window.mesh_dock import DisplayMode


_applyDisplayMode = {
    DisplayMode.DISPLAY_MODE_POINTS.value         : lambda actor: _applyPointsMode(actor),
    DisplayMode.DISPLAY_MODE_WIREFRAME.value      : lambda actor: _applyWireframeMode(actor),
    DisplayMode.DISPLAY_MODE_SURFACE.value        : lambda actor: _applySurfaceMode(actor),
    DisplayMode.DISPLAY_MODE_SURFACE_EDGE.value   : lambda actor: _applySurfaceEdgeMode(actor),
    DisplayMode.DISPLAY_MODE_FEATURE.value        : lambda actor: _applyFeatureMode(actor)
}


def _applyPointsMode(actor):
    actor.GetProperty().SetPointSize(3)
    actor.GetProperty().SetColor(0.1, 0.0, 0.3)
    actor.GetProperty().SetRepresentationToPoints()


def _applyWireframeMode(actor):
    actor.GetProperty().SetColor(0.1, 0.0, 0.3)
    actor.GetProperty().SetLineWidth(1.0)
    actor.GetProperty().SetRepresentationToWireframe()


def _applySurfaceMode(actor):
    actor.GetProperty().SetColor(0.5, 0.2, 1.0)
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().EdgeVisibilityOff()


def _applySurfaceEdgeMode(actor):
    actor.GetProperty().SetColor(0.5, 0.2, 1.0)
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetEdgeColor(0.1, 0.0, 0.3)
    actor.GetProperty().SetLineWidth(1.0)


def _applyFeatureMode(actor):
    actor.GetProperty().SetColor(0.5, 0.2, 1.0)
    actor.GetProperty().SetEdgeColor(0.1, 0.0, 0.3)
    actor.GetProperty().SetLineWidth(1.0)


def _applyHighlight(actor):
    actor.GetProperty().SetColor(1, 1, 1)
    actor.GetProperty().SetEdgeColor(1, 1, 1)
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetRepresentationToSurface()


class ActorInfo:
    def __init__(self, face, feature=None):
        self._visibility = True
        self._selected = False
        self._face = face
        self._feature = feature

    @property
    def face(self):
        return self._face

    @property
    def feature(self):
        return self._feature

    def actor(self, featureMode):
        return self._feature if featureMode else self._face

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

        self._view = app.meshDock
        self._actorInfos = {}
        self._currentId = None
        self._featureMode = False
        self._hasFeatures = True
        self._bounds = None

    def activate(self):
        displayMode = self._view.displayMode()
        self._featureMode = displayMode == DisplayMode.DISPLAY_MODE_FEATURE and self._hasFeatures
        for actorInfo in self._actorInfos.values():
            if actorInfo.visibility:
                actor = actorInfo.actor(self._featureMode)
                _applyDisplayMode[displayMode](actor)
                self._view.addActor(actor)

    def deactivate(self):
        for actorInfo in self._actorInfos.values():
            if actorInfo.visibility:
                self._view.removeActor(actorInfo.actor(self._featureMode))

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
        self._view.update()

    def hideActor(self, id_):
        if self._actorInfos[id_].visibility:
            self._view.removeActor(self._actorInfos[id_].actor(self._featureMode))

        self._actorInfos[id_].visibility = False
        self._view.update()

    def actorPicked(self, actor):
        self.setCurrentId(self._findActorInfo(actor))
        self.currentActorChanged.emit()

    def setCurrentId(self, id_):
        self._highlightActor(id_)
        self._currentId = id_

    def changeDisplayMode(self, displayMode):
        if displayMode == DisplayMode.DISPLAY_MODE_FEATURE.value and self._hasFeatures:
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

    def showCulling(self):
        for a in self._actorInfos.values():
            a.actor(self._featureMode).GetProperty().FrontfaceCullingOn()

    def hideCulling(self):
        for a in self._actorInfos.values():
            a.actor(self._featureMode).GetProperty().FrontfaceCullingOff()

    def fullBounds(self):
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

    def _findActorInfo(self, actor):
        for id_ in self._actorInfos:
            if self._actorInfos[id_].actor(self._featureMode) == actor:
                return id_

        return None

    def _highlightActor(self, id_):
        # Reset properties of unselected actors
        if currentActor := self.currentActor():
            _applyDisplayMode[self._view.displayMode()](currentActor)

        actor = None
        if id_:
            _applyHighlight(self._actorInfos[id_].actor(self._featureMode))

        if actor != currentActor:
            self._view.update()

    def _applyDisplayMode(self, actor):
        if actor == self.currentActor():
            _applyHighlight(actor)
        else:
            _applyDisplayMode[self._view.displayMode()](actor)
