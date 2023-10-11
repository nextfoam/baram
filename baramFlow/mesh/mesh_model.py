#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal

from baramFlow.app import app
from baramFlow.view.main_window.rendering_view import DisplayMode


_applyDisplayMode = {
    DisplayMode.DISPLAY_MODE_POINTS         : lambda actor: _applyPointsMode(actor),
    DisplayMode.DISPLAY_MODE_WIREFRAME      : lambda actor: _applyWireframeMode(actor),
    DisplayMode.DISPLAY_MODE_SURFACE        : lambda actor: _applySurfaceMode(actor),
    DisplayMode.DISPLAY_MODE_SURFACE_EDGE   : lambda actor: _applySurfaceEdgeMode(actor),
    DisplayMode.DISPLAY_MODE_FEATURE        : lambda actor: _applyFeatureMode(actor)
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
