#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

from settings.local_settings import LocalSettings
from db.configurations import Configurations
from db.configurations_schema import schema


class Project(QObject):
    def __init__(self, path):
        super().__init__()

        self._settings = LocalSettings(path)
        self._path = self._settings.path
        self._lock = None
        self._db = Configurations(schema)

    @property
    def path(self):
        return self._path

    def name(self):
        return self.path.name

    def db(self):
        return self._db

    def getLocalSetting(self, key):
        return self._settings.get(key)

    def setLocalSetting(self, key, value):
        self._settings.set(key, value)

    def save(self):
        self._db.save()

    def saveAs(self, directory):
        # self._fileDB.saveAs(directory)
        # self._close()
        # self._open(directory, ProjectOpenType.SAVE_AS)
        # self.projectOpened.emit()
        return

    def open(self):
        self._settings.acquireLock(0.01)
        self._db.load(self._path)

    def close(self):
        self._settings.releaseLock()
