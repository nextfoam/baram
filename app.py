#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTranslator, QCoreApplication, QLocale

from resources import resource
from settings.app_settings import AppSettings
from settings.project_manager import ProjectManager
from openfoam.file_system import FileSystem


if getattr(sys, 'frozen', False):
    APP_PATH = Path(sys.executable).parent.resolve()
else:
    APP_PATH = Path(__file__).parent.resolve()


class App(QObject):
    def __init__(self):
        super().__init__()

        self._properties = None
        self._settings = None
        self._project = None
        self._fileSystem = None

        self._window = None
        self._translator = None
        self._projectManager = ProjectManager()

    @property
    def properties(self):
        return self._properties

    @property
    def settings(self):
        return self._settings

    @property
    def window(self):
        return self._window

    @property
    def project(self):
        return self._project

    @property
    def fileSystem(self):
        return self._fileSystem

    @property
    def db(self):
        return self._project.db() if self._project else None

    @window.setter
    def window(self, window):
        self._window = window

    def setupApplication(self, properties):
        self._properties = properties
        self._settings = AppSettings(properties.name)

    def applyLanguage(self):
        QCoreApplication.removeTranslator(self._translator)
        self._translator = QTranslator()
        self._translator.load(QLocale(QLocale.languageToCode(QLocale(self._settings.getLanguage()).language())),
                              'baram', '_', str(resource.file('locale')))
        QCoreApplication.installTranslator(self._translator)

    def createProject(self, path):
        assert(self._project is None)

        self._project = self._projectManager.createProject(path)
        self._settings.updateRecents(self._project.path, True)
        self._fileSystem = FileSystem(self._project.path)
        self._fileSystem.createCase(APP_PATH / 'resources/openfoam/case')

        return self._project

    def openProject(self, path):
        assert(self._project is None)

        self._project = self._projectManager.openProject(path)
        self._settings.updateRecents(self._project.path)
        self._fileSystem = FileSystem(self._project.path)

        return self._project

    def closeProject(self):
        if self._project:
            self._project.close()
        self._project = None


app = App()
