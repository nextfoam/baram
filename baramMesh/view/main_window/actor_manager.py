#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import QObject

from libbaram.mesh import Bounds
from baramMesh.app import app


class ActorGroup(Enum):
    GEOMETRY = auto()
    MESH = auto()


class ActorManager(QObject):
    def __init__(self):
        super().__init__()

        self._actorInfos = {}
        self._visibility = True
        self._displayControl = app.window.displayControl

    def isEmpty(self):
        return not self._actorInfos

    def actorInfo(self, key):
        return self._actorInfos.get(key)

    def add(self, actorInfo):
        if actorInfo.id() in self._actorInfos:
            raise KeyError

        self._actorInfos[actorInfo.id()] = self._displayControl.add(actorInfo)

    def update(self, id_, dataSet):
        self._actorInfos[id_].setDataSet(dataSet)

    def remove(self, key):
        if actorInfo := self._actorInfos.pop(key, None):
            self._displayControl.remove(actorInfo)

    def getBounds(self) -> Optional[Bounds]:
        if self.isEmpty():
            return None

        it = iter(self._actorInfos.values())
        bounds = next(it).bounds()
        while actorInfo := next(it, None):
            bounds.merge(actorInfo.bounds())

        return bounds

    def applyToDisplay(self):
        self._displayControl.refreshView()

    def fitDisplay(self):
        self._displayControl.fitView()

    def clear(self):
        self.hide()
        self._actorInfos.clear()

    def hide(self):
        for actorInfo in self._actorInfos.values():
            self._displayControl.hide(actorInfo)

        self._displayControl.refreshView()
        self._visibility = False

    def clip(self, planes):
        for actorInfo in self._actorInfos.values():
            actorInfo.clip(planes)

        self._displayControl.refreshView()

    def slice(self, plane):
        for actorInfo in self._actorInfos.values():
            actorInfo.slice(plane)

        self._displayControl.refreshView()

    def _show(self):
        for actorInfo in self._actorInfos.values():
            self._displayControl.add(actorInfo)

        self._displayControl.refreshView()
        self._visibility = True

    def _updateActorName(self, id_, name):
        self._actorInfos[id_].setName(name)
