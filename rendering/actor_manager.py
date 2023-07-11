#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .actor_info import ActorInfo


class ActorManager:
    def __init__(self, view):
        self._view = view
        self._actors = {}

    def add(self, actor, name):
        self._actors[name] = ActorInfo(actor, name)
        self._view.addActor(actor)

    def remove(self, name):
        if name in self._actors:
            self._view.removeActor(self._actors[name].actor())
            self._actors[name] = None

    def replace(self, actor, name):
        new = ActorInfo(actor, name)

        if name in self._actors:
            old = self._actors[name]
            new.setVisible(old.isVisible())
            if old.isVisible():
                self._view.removeActor(old.actor())

        self._actors[name] = new
        if new.isVisible():
            self._view.addActor(actor)
            self._view.refresh()

    def show(self, name):
        if name in self._actors and not self._actors[name].isVisible():
            self._view.addActor(self._actors[name].actor())
            self._actors[name].setVisible(True)

        self._view.refresh()

    def hide(self, name):
        if name in self._actors and self._actors[name].isVisible():
            self._view.removeActor(self._actors[name].actor())
            self._actors[name].setVisible(False)

        self._view.refresh()

    def fitCamera(self):
        self._view.fitCamera()

    def refresh(self):
        self._view.refresh()