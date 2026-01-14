#!/usr/bin/env python
# -*- coding: utf-8 -*-

_expertModeActivated = False


class IExpertModeObserver():
    def expertModeAtivated(self):
        pass


_observers: list[IExpertModeObserver] = []


def registerObserver(observer):
    _observers.append(observer)


def isExpertModeActivated() -> bool:
    return _expertModeActivated


def activateExpertMode():
    global _expertModeActivated
    _expertModeActivated = True

    for observer in _observers:
        observer.expertModeAtivated()

