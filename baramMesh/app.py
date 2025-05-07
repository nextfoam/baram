#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from PySide6.QtCore import QObject, QTranslator, QCoreApplication, QLocale, Signal
from PySide6.QtWidgets import QApplication

from baramMesh.db.project import Project
from baramMesh.settings.app_settings import appSettings
from baramMesh.settings.project_manager import ProjectManager
from baramMesh.openfoam.file_system import FileSystem
from resources import resource


class App(QObject):
    renderingToggled = Signal(bool)

    def __init__(self):
        super().__init__()

        self._properties = None
        self._settings = None
        self._project: Optional[Project] = None
        self._fileSystem = None

        self._window = None
        self._translator = None
        self._projectManager = ProjectManager()

        self._qApplication: Optional[QApplication] = None

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

    @property
    def consoleView(self):
        return self._window.consoleView

    @window.setter
    def window(self, window):
        self._window = window

    @property
    def qApplication(self):
        return self._qApplication

    @qApplication.setter
    def qApplication(self, application):
        self._qApplication = application

    def setupApplication(self, properties):
        self._properties = properties
        appSettings.load(properties.name)
        self._settings = appSettings

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
        self._fileSystem.createCase(resource.file('openfoam/case'))

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
