#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from .rendering_manager import RenderingMode, rendering


_applySurfaceRednderingMode = {
    RenderingMode.SURFACE.value     : lambda actor: _applySurfaceMode(actor),
    RenderingMode.SURFACE_EDGE.value: lambda actor: _applySurfaceEdgeMode(actor),
}


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


def _applyHighlight(actor):
    actor.GetProperty().SetColor(1, 1, 1)
    actor.GetProperty().SetEdgeColor(1, 1, 1)
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetRepresentationToSurface()


class ActorGroup(Enum):
    GEOMETRY = auto()
    MESH = auto()


class ActorManager:
    class ActorInfoGroup:
        def __init__(self):
            self._members = {}
            self._visible = False

        def isVisible(self):
            return self._visible

        def setVisible(self, visible):
            self._visible = visible

        def add(self, actorInfo):
            if actorInfo.name in self._members:
               raise KeyError

            self._members[actorInfo.name] = actorInfo

        def pop(self, name):
            return self._members.pop(name, None)

        def get(self, name):
            return self._members[name]

        def replace(self, actorInfo):
            if actorInfo.name not in self._members:
                raise KeyError

            self._members[actorInfo.name] = actorInfo

        def getBounds(self):
            if not self._members:
                return None

            it = iter(self._members.values())
            bounds = next(it).bounds()
            while actorInfo := next(it, None):
                bounds.merge(actorInfo.bounds())

            return bounds

        def isEmpty(self):
            return not self._members

        def memebers(self):
            return self._members.items()

        def actorInfos(self):
            return self._members.values()

    def __init__(self, view):
        self._view = view
        self._actorInfos = {group: self.ActorInfoGroup() for group in ActorGroup}

        rendering.renderingModeChanged.connect(self._applyRenderingMode)

    def add(self, actorInfo, group):
        self._actorInfos[group].add(actorInfo)

        if self._actorInfos[group].isVisible() and actorInfo.isVisible():
            self._show(actorInfo)
            self._view.refresh()

    def remove(self, name, group):
        if actorInfo := self._actorInfos[group].pop(name):
            if self._actorInfos[group].isVisible() and actorInfo.isVisible():
                self._hide(actorInfo)
                self._view.refresh()

    def replace(self, actorInfo, name, group):
        old = self._actorInfos[group].get(name)

        actorInfo.setVisible(old.isVisible())
        if self._actorInfos[group].isVisible() and old.isVisible():
            self._hide(old)

        actorInfo.name = name
        self._actorInfos[group].replace(actorInfo)
        if self._actorInfos[group].isVisible() and actorInfo.isVisible():
            self._show(actorInfo)
            self._view.refresh()

    def show(self, name, group):
        actorInfo = self._actorInfos[group].get(name)
        if self._actorInfos[group].isVisible() and not actorInfo.isVisible():
            self._show(actorInfo)

        self._view.refresh()

    def hide(self, name, group):
        actorInfo = self._actorInfos[group].get(name)
        if self._actorInfos[group].isVisible() and actorInfo.isVisible():
            self._hide(actorInfo)

        self._view.refresh()

    def showGroup(self, group):
        if not self._actorInfos[group].isVisible():
            for actorInfo in self._actorInfos[group].actorInfos():
                self._show(actorInfo)

            self._view.fitCamera()
            self._actorInfos[group].setVisible(True)

    def hideGroup(self, group):
        if self._actorInfos[group].isVisible():
            for actorInfo in self._actorInfos[group].actorInfos():
                self._hide(actorInfo)

            self._view.fitCamera()
            self._actorInfos[group].setVisible(False)

    def getBounds(self, group):
        return self._actorInfos[group].getBounds()

    def isEmpty(self, group):
        return self._actorInfos[group].isEmpty()

    def _show(self, actorInfo):
        if actor := actorInfo.actor(rendering.actorMode()):
            self._view.addActor(actor)
            actorInfo.setVisible(True)

    def _hide(self, actorInfo):
        if actor := actorInfo.actor(rendering.actorMode()):
            self._view.removeActor(actor)
            actorInfo.setVisible(False)

    def _applyRenderingMode(self, old, new):
        if old == new:
            return

        if old == RenderingMode.FEATURE.value:
            for groupActors in self._actorInfos.values():
                for gId, actorInfo in groupActors.memebers():
                    _applySurfaceRednderingMode[new](actorInfo.surface)
                    if actorInfo.feature:
                        self._view.removeActor(actorInfo.feature)
                    self._show(actorInfo)
        elif new == RenderingMode.FEATURE.value:
            for groupActors in self._actorInfos.values():
                for gId, actorInfo in groupActors.memebers():
                    self._view.removeActor(actorInfo.surface)
                    if actorInfo.feature:
                        self._show(actorInfo)
        else:
            for groupActors in self._actorInfos.values():
                for actorInfo in groupActors.actorInfos():
                    print(actorInfo)
                    _applySurfaceRednderingMode[new](actorInfo.surface)

        self._view.refresh()
