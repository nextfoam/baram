#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QObject

from app import app


class ActorGroup(Enum):
    GEOMETRY = auto()
    MESH = auto()


class ActorManager(QObject):
    def __init__(self):
        super().__init__()

        self._actorInfos = {}
        self._visibility = True
        self._displayController = app.window.displayControl

        self._name = None

    def isEmpty(self):
        return not self._actorInfos

    def add(self, actorInfo):
        if actorInfo.id() in self._actorInfos:
            raise KeyError

        self._actorInfos[actorInfo.id()] = actorInfo
        self._displayController.add(actorInfo)

    def remove(self, key):
        if actorInfo := self._actorInfos.pop(key, None):
            self._displayController.remove(actorInfo)

    def getBounds(self):
        if self.isEmpty():
            return None

        it = iter(self._actorInfos.values())
        bounds = next(it).bounds()
        while actorInfo := next(it, None):
            bounds.merge(actorInfo.bounds())

        return bounds

    def applyToDisplay(self):
        self._displayController.refreshView()

    def fitDisplay(self):
        self._displayController.fitView()

    def clear(self):
        self.hide()
        self._actorInfos.clear()

    def hide(self):
        for actorInfo in self._actorInfos.values():
            self._displayController.remove(actorInfo)

        self._displayController.refreshView()
        self._visibility = False

    def _show(self):
        for actorInfo in self._actorInfos.values():
            self._displayController.add(actorInfo)

        self._displayController.refreshView()
        self._visibility = True
