#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import shutil
from enum import IntEnum, auto

from PySide6.QtCore import QObject, Signal


class CaseStatus(IntEnum):
    NONE = 0
    CREATED = auto()
    MESH_LOADED = auto()


class CaseSignals(QObject):
    statusChanged = Signal(CaseStatus)


class Settings:
    _workingDirectory = None
    _settingsDirectory = None
    _status = -1

    signals = CaseSignals()

    @classmethod
    def createWorkspace(cls, directory):
        cls._workingDirectory = directory
        cls._settingsDirectory = os.path.join(directory, '.baram')

        if os.path.isdir(cls._settingsDirectory):
            shutil.rmtree(cls._settingsDirectory)
        os.mkdir(cls._settingsDirectory)

        cls.setStatus(CaseStatus.CREATED)

    @classmethod
    def workingDirectory(cls):
        return cls._workingDirectory

    @classmethod
    def settingsDirectory(cls):
        return cls._settingsDirectory

    @classmethod
    def setStatus(cls, status):
        cls._status = status
        cls.signals.statusChanged.emit(status)

    @classmethod
    def isMeshLoaded(cls):
        return cls._status >= CaseStatus.MESH_LOADED
