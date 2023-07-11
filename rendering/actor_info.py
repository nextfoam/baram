#!/usr/bin/env python
# -*- coding: utf-8 -*-


class ActorInfo:
    def __init__(self, actor, name, group=None):
        self._actor = actor
        self._feature = None
        self._group = group

        self._visibility = True

        self._actor.SetObjectName(name)

    def actor(self):
        return self._actor

    def isVisible(self):
        return self._visibility

    def setVisible(self, visibility):
        self._visibility = visibility
